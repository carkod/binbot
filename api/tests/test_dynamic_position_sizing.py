from typing import cast
from types import SimpleNamespace
from unittest.mock import MagicMock
from pathlib import Path
import warnings

import pytest
from kucoin_universal_sdk.model.common import RestError
from pybinbot import (
    BinanceKlineIntervals,
    BotModel,
    DealType,
    MarketType,
    OrderModel,
    OrderStatus,
    Position,
    Status,
)
from sqlalchemy import create_engine, inspect, text
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from pybinbot.models.deal import PositionSizeOrder

from api.alembic.versions import a7b4e9c261f0_dynamic_position_sizing as migration
from api.databases.crud.bot_crud import BotTableCrud
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from api.exchange_apis.kucoin.futures.position_sizing import DynamicPositionSizing
from streaming.base import BaseStreaming
from streaming.lifecycle import Lifecycle
from streaming.context_evaluator import LifecycleEvaluation
from streaming.strategies.base import LifecyclePolicy, LifecycleSignal
from sqlmodel import SQLModel, Session
from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable


def execution(*, short=False):
    bot = BotModel(
        pair="XBTUSDTM",
        fiat="USDT",
        futures_leverage=3,
        market_type=MarketType.FUTURES,
        status=Status.active,
        dynamic_position_sizing=True,
        trailing=True,
        stop_loss=5,
        take_profit=10,
        trailing_profit=5,
        trailing_deviation=2,
        position=Position.short if short else Position.long,
        deal={"opening_price": 100, "opening_qty": 100, "current_position_qty": 100},
    )
    result = MagicMock(spec=KucoinPositionDeal)
    result.active_bot = bot
    result.price_precision = 2
    result.TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO = (
        KucoinPositionDeal.TRAILING_STOP_REFRESH_MIN_IMPROVEMENT_RATIO
    )
    result._direction_multiplier.return_value = -1 if short else 1
    result._is_recovery_bot.return_value = False
    result.awaiting_close_confirmation.side_effect = lambda: (
        KucoinPositionDeal.awaiting_close_confirmation(result)
    )
    result.close_all.return_value = bot
    result.last_trailing_stop_replace_ts_ms.return_value = None
    result.trailing_stop_replace_on_cooldown.return_value = False
    result.should_refresh_trailing_stop_loss.side_effect = lambda **kwargs: (
        KucoinPositionDeal.should_refresh_trailing_stop_loss(result, **kwargs)
    )
    result.controller = MagicMock(spec=BotTableCrud)
    result.kucoin_symbol = bot.pair
    result.kucoin_symbol_data = SimpleNamespace(lot_size=1)
    result.symbol_info = SimpleNamespace(futures_leverage=1)
    result.kucoin_futures_api = MagicMock()
    result.kucoin_futures_api.get_futures_position.return_value = SimpleNamespace(
        current_qty=-100 if short else 100
    )
    result.required_margin_for_contracts.return_value = 30
    result.kucoin_futures_api.futures_account_api.get_futures_account.return_value = (
        SimpleNamespace(available_balance=100)
    )
    result.kucoin_futures_api.futures_order_api.get_order_by_client_oid.return_value = (
        SimpleNamespace(
            is_active=False,
            filled_size=25,
            avg_deal_price=95,
            id="adjustment-1",
            end_at=1000,
            updated_at=1000,
            created_at=1000,
        )
    )
    return result


def make_lifecycle(engine, monkeypatch):
    lifecycle = Lifecycle(
        engine,
        cast(
            BaseStreaming,
            SimpleNamespace(interval=BinanceKlineIntervals.fifteen_minutes),
        ),
    )
    lifecycle.klines = []
    monkeypatch.setattr(
        lifecycle,
        "_evaluate_strategy",
        lambda **kwargs: LifecycleEvaluation(LifecyclePolicy(), LifecycleSignal()),
    )
    return lifecycle


@pytest.mark.parametrize("short,price", [(False, 94), (True, 106)])
def test_stop_hit_closes_whole_position_without_sizing_reductions(
    monkeypatch, short, price
):
    engine = execution(short=short)
    make_lifecycle(engine, monkeypatch).exit(price)
    engine.close_all.assert_called_once_with(deal_type=DealType.stop_loss)
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()


@pytest.mark.parametrize("price", [90, 95, 100, 110])
def test_sizing_does_nothing_without_a_trailing_profit_trigger(price):
    engine = execution()
    assert DynamicPositionSizing(engine).process(price) is False
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()


@pytest.mark.parametrize("short,price,side", [(False, 110, "buy"), (True, 90, "sell")])
def test_profit_hit_increases_using_bot_leverage_and_confirmed_fill(short, price, side):
    engine = execution(short=short)
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.return_value.avg_deal_price = price
    api.get_order_by_client_oid.return_value.filled_size = 10  # terminal partial fill
    DynamicPositionSizing(engine).process(price, trailing_profit_reached=True)
    request = api.add_order.call_args.args[0]
    assert request.reduce_only is False
    assert request.side.value == side
    assert request.leverage == 3
    engine.required_margin_for_contracts.assert_called_once_with(25, price)
    assert engine.active_bot.deal.current_position_qty == 110
    assert engine.active_bot.deal.opening_price == pytest.approx(
        (10000 + price * 10) / 110
    )


def test_insufficient_funds_returns_control_to_trailing_without_fixed_tp():
    engine = execution()
    engine.kucoin_futures_api.futures_account_api.get_futures_account.return_value.available_balance = 2
    assert (
        DynamicPositionSizing(engine).process(111, trailing_profit_reached=True)
        is False
    )
    bot = engine.active_bot
    assert not bot.dynamic_position_sizing
    assert bot.trailing
    assert bot.take_profit == 0
    assert any("insufficient futures funds" in log for log in bot.logs)
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()
    engine.reconcile_exchange_sl.assert_called_once()


def test_balance_rejection_falls_back_but_network_error_keeps_pending_intent():
    engine = execution()
    api = engine.kucoin_futures_api.futures_order_api
    api.add_order.side_effect = RestError(
        msg="balance",
        response=SimpleNamespace(code="300003", message="Balance insufficient"),
    )
    assert (
        DynamicPositionSizing(engine).process(111, trailing_profit_reached=True)
        is False
    )
    assert engine.active_bot.deal.position_size_order is None
    engine = execution()
    api = engine.kucoin_futures_api.futures_order_api
    api.add_order.side_effect = TimeoutError("unknown submission outcome")
    with pytest.raises(TimeoutError):
        DynamicPositionSizing(engine).process(111, trailing_profit_reached=True)
    pending_id = engine.active_bot.deal.position_size_order.client_oid
    api.get_order_by_client_oid.return_value.is_active = True
    api.get_order_by_client_oid.return_value.filled_size = 0
    DynamicPositionSizing(engine).process(115)
    assert api.add_order.call_count == 1
    assert api.get_order_by_client_oid.call_args.args[0].client_oid == pending_id
    assert engine.active_bot.deal.current_position_qty == 100


def test_pre_submission_crash_restores_normal_exits_without_an_exchange_order():
    engine = execution()
    snapshot = None

    def crash_after_intent_save(bot):
        nonlocal snapshot
        if bot.deal.position_size_order is not None:
            snapshot = bot.model_dump()
            raise RuntimeError("worker stopped after commit")

    engine.controller.save.side_effect = crash_after_intent_save
    with pytest.raises(RuntimeError):
        DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    engine.active_bot = BotModel.model_validate(snapshot)
    assert engine.active_bot.deal.position_size_order.submission_phase == "prepared"
    engine.controller.save.side_effect = None
    assert DynamicPositionSizing(engine).process(94) is False
    assert engine.active_bot.deal.position_size_order is None
    assert not engine.active_bot.dynamic_position_sizing
    engine.reconcile_exchange_sl.assert_called_once()
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()
    engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.assert_not_called()


def pending_order(*, reducing=False):
    return PositionSizeOrder(
        client_oid="persisted-before-crash",
        reducing=reducing,
        quantity_before=100,
        entry_price_before=100,
        requested_qty=25,
        signal_price=95 if reducing else 110,
    )


def missing_order_error():
    return RestError(
        msg="missing",
        response=SimpleNamespace(code="100001", message="Order does not exist"),
    )


def test_restarted_unknown_intent_replays_same_id_after_bounded_not_found(monkeypatch):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = missing_order_error()
    for now in (100, 130, 160):
        monkeypatch.setattr(
            "api.exchange_apis.kucoin.futures.position_sizing.time", lambda: now
        )
        DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
        # Every tick hydrates from saved state as a new worker would.
        engine.active_bot = BotModel.model_validate(engine.active_bot.model_dump())
        if now < 160:
            api.add_order.assert_not_called()
    api.add_order.assert_called_once()
    assert api.add_order.call_args.args[0].client_oid == "persisted-before-crash"
    assert engine.active_bot.deal.current_position_qty == 100
    api.get_order_by_client_oid.side_effect = None
    DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    assert engine.active_bot.deal.current_position_qty == 125
    assert engine.active_bot.deal.position_size_order is None
    assert len(engine.active_bot.orders) == 1


def test_duplicate_replay_response_preserves_pending_until_fill_is_visible(monkeypatch):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    engine.active_bot.deal.position_size_order.not_found_since_ms = 100_000
    engine.active_bot.deal.position_size_order.not_found_count = 2
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.position_sizing.time", lambda: 160
    )
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = missing_order_error()
    api.add_order.side_effect = RestError(
        msg="duplicate",
        response=SimpleNamespace(code="300018", message="clientOid parameter repeated"),
    )
    DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    assert (
        engine.active_bot.deal.position_size_order.client_oid
        == "persisted-before-crash"
    )
    assert not engine.active_bot.orders
    api.get_order_by_client_oid.side_effect = None
    DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    assert engine.active_bot.deal.current_position_qty == 125
    api.add_order.assert_called_once()


@pytest.mark.parametrize(
    "code,message",
    [
        ("100001", "Invalid parameter"),
        ("429000", "Too many requests"),
        ("500000", "Internal server error"),
    ],
)
def test_lookup_errors_are_not_treated_as_missing_orders(code, message):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = RestError(
        msg=message, response=SimpleNamespace(code=code, message=message)
    )
    with pytest.raises(RestError):
        DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    assert engine.active_bot.deal.position_size_order.not_found_count == 0
    api.add_order.assert_not_called()


def test_missing_increase_rechecks_margin_and_keeps_normal_exits_after_fallback(
    monkeypatch,
):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order(reducing=False)
    engine.active_bot.deal.position_size_order.not_found_since_ms = 100_000
    engine.active_bot.deal.position_size_order.not_found_count = 2
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.position_sizing.time", lambda: 160
    )
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = missing_order_error()
    engine.kucoin_futures_api.futures_account_api.get_futures_account.return_value.available_balance = 0
    assert (
        DynamicPositionSizing(engine).process(111, trailing_profit_reached=True)
        is False
    )
    engine.required_margin_for_contracts.assert_called_once_with(25, 111)
    assert (
        engine.active_bot.deal.position_size_order.client_oid
        == "persisted-before-crash"
    )
    engine.reconcile_exchange_sl.assert_called_once()
    # Retain the identity without blocking exits or retrying when funds recover.
    engine.kucoin_futures_api.futures_account_api.get_futures_account.return_value.available_balance = 100
    assert DynamicPositionSizing(engine).process(112) is False
    api.get_order_by_client_oid.side_effect = RestError(
        msg="rate limit",
        response=SimpleNamespace(code="429000", message="Too many requests"),
    )
    assert DynamicPositionSizing(engine).process(112) is False
    api.add_order.assert_not_called()


def test_missing_count_resets_on_visible_order_and_requires_time_grace(monkeypatch):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = missing_order_error()
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.position_sizing.time", lambda: 100
    )
    for _ in range(4):
        DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    api.add_order.assert_not_called()
    api.get_order_by_client_oid.side_effect = None
    api.get_order_by_client_oid.return_value.is_active = True
    DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    assert engine.active_bot.deal.position_size_order.not_found_count == 0
    assert engine.active_bot.deal.position_size_order.not_found_since_ms == 0


def test_migration_graph_keeps_grid_revision_and_has_unique_ids():
    directory = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "alembic"))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        revisions = list(directory.walk_revisions())
    assert len({item.revision for item in revisions}) == len(revisions)
    assert directory.get_revision("d2e3f4a5b6c7").path.endswith(
        "add_grid_signal_payload_fields.py"
    )
    assert directory.get_revision("a0e265d5cb35").down_revision == "d2e3f4a5b6c7"
    assert directory.get_revision(migration.revision).path.endswith(
        "dynamic_position_sizing.py"
    )


@pytest.mark.parametrize("short", [False, True])
def test_active_partial_fills_resize_protection_and_count_cumulative_fills_once(short):
    engine = execution(short=short)
    bot = engine.active_bot
    api = engine.kucoin_futures_api.futures_order_api
    fill = api.get_order_by_client_oid.return_value
    fill.is_active = True
    fill.filled_size = 4
    fill.avg_deal_price = 90 if short else 110
    sizing = DynamicPositionSizing(engine)
    sizing.process(fill.avg_deal_price, trailing_profit_reached=True)
    assert bot.deal.current_position_qty == 104
    assert bot.deal.base_order_size == 104
    assert bot.deal.opening_price == pytest.approx(
        (10000 + 4 * fill.avg_deal_price) / 104
    )
    assert bot.deal.position_size_order is not None
    assert not bot.orders  # Record one cumulative order when it becomes terminal.
    engine.reconcile_exchange_sl.assert_called_once_with(position_qty=104)

    # Re-polling the same cumulative fill must not add it again.
    sizing.process(fill.avg_deal_price)
    assert bot.deal.current_position_qty == 104
    assert engine.reconcile_exchange_sl.call_count == 2
    fill.filled_size = 10
    fill.avg_deal_price = 88 if short else 112
    sizing.process(fill.avg_deal_price)
    assert bot.deal.current_position_qty == 110
    assert bot.deal.opening_price == pytest.approx(
        (10000 + 10 * fill.avg_deal_price) / 110
    )
    engine.reconcile_exchange_sl.assert_called_with(position_qty=110)

    # A terminal partial fill finalizes the same cumulative quantity, not +10.
    fill.is_active = False
    sizing.process(fill.avg_deal_price)
    assert bot.deal.current_position_qty == 110
    assert bot.deal.opening_qty == 100
    assert bot.deal.position_size_order is None
    assert len(bot.orders) == 1
    assert bot.orders[0].qty == 10
    assert bot.orders[0].price == fill.avg_deal_price
    api.add_order.assert_called_once()


@pytest.mark.parametrize("active", [True, False])
def test_partial_fill_with_delayed_price_still_resizes_protection(active):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    fill = (
        engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.return_value
    )
    fill.is_active = active
    fill.filled_size = 6
    fill.avg_deal_price = 0
    DynamicPositionSizing(engine).process(110)
    assert engine.active_bot.deal.current_position_qty == 106
    assert engine.active_bot.deal.opening_price == 100
    assert engine.active_bot.deal.position_size_order is not None
    engine.reconcile_exchange_sl.assert_called_once_with(position_qty=106)
    assert not engine.active_bot.orders


@pytest.mark.parametrize("short", [False, True])
def test_active_partial_fill_survives_database_restart_without_double_counting(short):
    engine = execution(short=short)
    db = create_engine("sqlite://")
    SQLModel.metadata.create_all(db)
    with Session(db) as session:
        row = BotTable(id=engine.active_bot.id, pair="XBTUSDTM", deal=DealTable())
        session.add(row)
        session.commit()
        engine.controller = BotTableCrud(session)
        api = engine.kucoin_futures_api.futures_order_api
        fill = api.get_order_by_client_oid.return_value
        fill.is_active = True
        fill.filled_size = 5
        fill.avg_deal_price = 90 if short else 110
        DynamicPositionSizing(engine).process(
            fill.avg_deal_price, trailing_profit_reached=True
        )
        session.expire_all()
        engine.active_bot = BotModel.dump_from_table(session.get(BotTable, row.id))
        assert engine.active_bot.deal.current_position_qty == 105
        assert engine.active_bot.deal.position_size_order.quantity_before == 100
        DynamicPositionSizing(engine).process(fill.avg_deal_price)
        assert engine.active_bot.deal.current_position_qty == 105
        fill.is_active = False
        fill.filled_size = 25
        fill.avg_deal_price = 88 if short else 112
        DynamicPositionSizing(engine).process(fill.avg_deal_price)
        assert engine.active_bot.deal.current_position_qty == 125
        assert engine.active_bot.deal.opening_price == pytest.approx(
            (10000 + 25 * fill.avg_deal_price) / 125
        )
        assert engine.active_bot.deal.position_size_order is None
        assert len(engine.active_bot.orders) == 1
        assert engine.active_bot.orders[0].qty == 25
        api.add_order.assert_called_once()


@pytest.mark.parametrize(
    "qty,pct,lot,expected",
    [(99, 25, 1, 24), (100, 25, 10, 20), (1, 25, 1, 0), (100, 100, 1, 100)],
)
def test_adjustment_rounds_down_to_exchange_lot(qty, pct, lot, expected):
    assert DynamicPositionSizing.adjustment_quantity(qty, pct, lot) == expected


@pytest.mark.parametrize("short,price", [(False, 105), (True, 95)])
def test_trailing_profit_arms_protection_and_increases_once_per_trigger(
    monkeypatch, short, price
):
    engine = execution(short=short)
    bot = engine.active_bot
    bot.take_profit = 1  # Fixed TP must not close a sizing bot.
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.return_value.avg_deal_price = price
    lifecycle = make_lifecycle(engine, monkeypatch)
    lifecycle.exit(price)
    stop = bot.deal.trailing_stop_loss_price
    trigger = bot.deal.trailing_profit_price
    assert stop == pytest.approx(price * (1.02 if short else 0.98))
    assert trigger == pytest.approx(price * (0.95 if short else 1.05))
    assert bot.deal.current_position_qty == 125
    engine.place_trailing_stop_loss.assert_called_once()
    engine.reconcile_exchange_sl.assert_called_once()
    engine.take_profit_order.assert_not_called()
    engine.close_all.assert_not_called()
    # Restarting and observing the same price cannot repeat an increase.
    engine.active_bot = BotModel.model_validate(bot.model_dump())
    make_lifecycle(engine, monkeypatch).exit(price)
    api.add_order.assert_called_once()
    assert engine.active_bot.deal.trailing_stop_loss_price == stop
    assert engine.active_bot.deal.trailing_profit_price == trigger


@pytest.mark.parametrize("short,price", [(False, 105), (True, 95)])
def test_stop_filled_during_trailing_placement_prevents_same_tick_scale_in(
    monkeypatch, short, price
):
    engine = execution(short=short)

    def fill_stop():
        engine.active_bot.orders.append(
            OrderModel(
                order_id="trailing-close",
                pair="XBTUSDTM",
                order_type="market",
                order_side="buy" if short else "sell",
                time_in_force="GTC",
                status=OrderStatus.FILLED,
                qty=100,
                requested_qty=100,
                price=0,
                deal_type=DealType.trailing_profit,
            )
        )

    engine.place_trailing_stop_loss.side_effect = fill_stop
    make_lifecycle(engine, monkeypatch).exit(price)
    assert engine.awaiting_close_confirmation()
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()


@pytest.mark.parametrize("short", [False, True])
def test_trailing_deviation_closes_full_position_even_with_pending_increase(
    monkeypatch, short
):
    engine = execution(short=short)
    stop = 95 if short else 105
    engine.active_bot.deal.trailing_stop_loss_price = stop
    engine.active_bot.deal.position_size_order = pending_order()
    # Equality triggers the exit and an unresolved lookup cannot block it.
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = missing_order_error()
    make_lifecycle(engine, monkeypatch).exit(stop)
    engine.close_all.assert_called_once_with(deal_type=DealType.trailing_profit)
    api.add_order.assert_not_called()
    api.get_order_by_client_oid.assert_not_called()


@pytest.mark.parametrize("short", [False, True])
def test_trailing_stop_never_loosens_on_rebound(monkeypatch, short):
    engine = execution(short=short)
    engine.active_bot.deal.trailing_stop_loss_price = 96 if short else 104
    engine.active_bot.deal.trailing_profit_price = 90 if short else 110
    make_lifecycle(engine, monkeypatch).exit(97 if short else 103)
    engine.close_all.assert_called_once_with(deal_type=DealType.trailing_profit)
    engine.place_trailing_stop_loss.assert_not_called()


def test_sand_rebound_closes_in_profit_instead_of_partially_buying_back(monkeypatch):
    engine = execution(short=True)
    bot = engine.active_bot
    engine.price_precision = 5
    bot.pair = "SANDUSDTM"
    bot.stop_loss = 5.6745
    bot.trailing_profit = 4.5
    bot.take_profit = 4.5
    bot.trailing_deviation = 3
    bot.deal.opening_price = 0.0632
    bot.deal.opening_qty = 24
    bot.deal.current_position_qty = 24
    api = engine.kucoin_futures_api.futures_order_api
    position = engine.kucoin_futures_api.get_futures_position.return_value
    position.current_qty = -24
    fill = api.get_order_by_client_oid.return_value
    fill.avg_deal_price = 0.06028
    fill.filled_size = 6
    lifecycle = make_lifecycle(engine, monkeypatch)
    lifecycle.exit(0.06028)
    assert bot.deal.current_position_qty == 30
    assert bot.deal.trailing_stop_loss_price == 0.06208
    position.current_qty = -30
    fill.avg_deal_price = 0.05745
    fill.filled_size = 7
    lifecycle.exit(0.05745)
    assert bot.deal.current_position_qty == 37
    assert bot.deal.trailing_stop_loss_price == 0.05917
    assert bot.deal.trailing_stop_loss_price < bot.deal.opening_price
    lifecycle.exit(0.06083)
    engine.close_all.assert_called_once_with(deal_type=DealType.trailing_profit)
    assert api.add_order.call_count == 2
    assert all(not call.args[0].reduce_only for call in api.add_order.call_args_list)


def test_pending_lookup_failure_does_not_block_full_stop_loss(monkeypatch):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.side_effect = (
        RestError(
            msg="lookup failed",
            response=SimpleNamespace(code="500000", message="failed"),
        )
    )
    make_lifecycle(engine, monkeypatch).exit(94)
    engine.close_all.assert_called_once_with(deal_type=DealType.stop_loss)


def test_pending_intent_serializes_through_bot_crud():
    engine = execution()
    engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.return_value.is_active = True
    DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
    table = BotTableCrud().update_table(engine.active_bot)
    assert isinstance(table.deal.position_size_order, dict)
    hydrated = BotModel.dump_from_table(table)
    assert (
        hydrated.deal.position_size_order == engine.active_bot.deal.position_size_order
    )
    assert hydrated.dynamic_position_sizing


def test_fallback_runs_normal_trailing_in_the_same_tick(monkeypatch):
    engine = execution()
    engine.price_precision = 2
    engine._direction_multiplier.return_value = 1
    engine._is_recovery_bot.return_value = False
    engine.kucoin_futures_api.futures_account_api.get_futures_account.return_value.available_balance = 0
    lifecycle = Lifecycle(
        engine,
        cast(
            BaseStreaming,
            SimpleNamespace(interval=BinanceKlineIntervals.fifteen_minutes),
        ),
    )
    lifecycle.klines = []
    monkeypatch.setattr(
        lifecycle,
        "_evaluate_strategy",
        lambda **kwargs: LifecycleEvaluation(LifecyclePolicy(), LifecycleSignal()),
    )
    lifecycle.exit(110)
    engine.place_trailing_stop_loss.assert_called_once()
    engine.take_profit_order.assert_not_called()
    assert engine.active_bot.deal.trailing_stop_loss_price == 107.8


def test_adjustments_and_pending_intent_survive_database_roundtrip():
    engine = execution()
    db = create_engine("sqlite://")
    SQLModel.metadata.create_all(db)
    table_type = BotTable
    with Session(db) as session:
        row = table_type(id=engine.active_bot.id, pair="XBTUSDTM", deal=DealTable())
        session.add(row)
        session.commit()
        engine.controller = BotTableCrud(session)
        engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.return_value.is_active = True
        DynamicPositionSizing(engine).process(95, trailing_profit_reached=True)
        saved = session.get(table_type, engine.active_bot.id)
        hydrated = BotModel.dump_from_table(saved)
        assert (
            hydrated.deal.position_size_order
            == engine.active_bot.deal.position_size_order
        )
        assert hydrated.dynamic_position_sizing


@pytest.mark.parametrize("partial", [False, True])
def test_migration_backfills_missing_or_existing_columns_and_replays(
    monkeypatch, partial
):
    db = create_engine("sqlite://")
    with db.begin() as connection:
        for table in ("bot", "paper_trading", "deal"):
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} (id) VALUES (1)"))
        if partial:
            connection.execute(
                text("ALTER TABLE deal ADD COLUMN position_size_pct FLOAT")
            )
            connection.execute(
                text("ALTER TABLE bot ADD COLUMN dynamic_position_sizing BOOLEAN")
            )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        migration.upgrade()
        assert (
            connection.execute(text("SELECT position_size_pct FROM deal")).scalar()
            == 25
        )
        assert (
            connection.execute(text("SELECT dynamic_position_sizing FROM bot")).scalar()
            == 0
        )
        connection.execute(text("UPDATE deal SET position_size_pct = 10"))
        migration.upgrade()
        assert (
            connection.execute(text("SELECT position_size_pct FROM deal")).scalar()
            == 10
        )
        migration.downgrade()
        migration.downgrade()
        assert {c["name"] for c in inspect(connection).get_columns("deal")} == {"id"}


@pytest.mark.parametrize(
    "message", ["Order does not exist", "error.getOrder.orderNotExist"]
)
def test_explicit_missing_order_message_counts_towards_recovery(message):
    engine = execution()
    engine.active_bot.deal.position_size_order = pending_order()
    engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.side_effect = (
        RestError(msg=message, response=SimpleNamespace(code="100001", message=message))
    )
    DynamicPositionSizing(engine).process(110)
    assert engine.active_bot.deal.position_size_order.not_found_count == 1


@pytest.mark.parametrize(
    "reducing,stop,trail,price",
    [
        (True, 0, 0, 110),  # Retire legacy partial reduction recovery.
        (False, 95, 0, 94),  # Full stop loss takes precedence.
        (False, 95, 105, 104),  # An armed trailing stop takes precedence.
    ],
)
def test_missing_order_recovery_never_replays_a_reduction_or_breached_exit(
    monkeypatch, reducing, stop, trail, price
):
    engine = execution()
    bot = engine.active_bot
    bot.deal.stop_loss_price = stop
    bot.deal.trailing_stop_loss_price = trail
    bot.deal.position_size_order = pending_order(reducing=reducing)
    bot.deal.position_size_order.not_found_since_ms = 100_000
    bot.deal.position_size_order.not_found_count = 2
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.position_sizing.time", lambda: 160
    )
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.side_effect = missing_order_error()
    DynamicPositionSizing(engine).process(price)
    api.add_order.assert_not_called()


def test_reconciled_increase_preserves_protective_prices():
    engine = execution()
    bot = engine.active_bot
    bot.deal.stop_loss_price = 95
    bot.deal.trailing_stop_loss_price = 107.8
    bot.deal.trailing_profit_price = 115.5
    bot.deal.position_size_order = pending_order()
    DynamicPositionSizing(engine).process(110)
    assert bot.deal.stop_loss_price == 95
    assert bot.deal.trailing_stop_loss_price == 107.8
    assert bot.deal.trailing_profit_price == 115.5
    engine.reconcile_exchange_sl.assert_called_once()


def test_native_trailing_fill_cancels_a_pending_increase_before_retiring_bot(
    monkeypatch,
):
    engine = execution()
    engine.active_bot.status = Status.completed
    engine.active_bot.deal.trailing_stop_loss_price = 105
    engine.active_bot.deal.position_size_order = pending_order()
    make_lifecycle(engine, monkeypatch).exit(104)
    engine.close_all.assert_called_once_with(deal_type=DealType.trailing_profit)
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()


@pytest.mark.parametrize(
    "trailing_stop_price,expected_deal_type",
    [(0, DealType.stop_loss), (105, DealType.trailing_profit)],
)
def test_process_tick_cleans_pending_increase_after_native_protective_fill(
    monkeypatch, trailing_stop_price, expected_deal_type
):
    engine = execution()
    bot = engine.active_bot
    bot.deal.position_size_order = pending_order()
    bot.deal.trailing_stop_loss_price = trailing_stop_price
    lifecycle = make_lifecycle(engine, monkeypatch)
    lifecycle.base_streaming.kucoin_futures_api = engine.kucoin_futures_api
    monkeypatch.setattr(
        lifecycle,
        "lifecycle_candle_intervals",
        lambda: (
            BinanceKlineIntervals.fifteen_minutes,
            BinanceKlineIntervals.fifteen_minutes,
        ),
    )

    class FilledProtectiveOrderPosition:
        def __init__(self, base_streaming, execution):
            self.base_streaming = base_streaming
            self.execution = execution
            self.df = None
            self.btc_df = None

        def dataframe_ops(self, **kwargs):
            return [], []

        def build_bb_metrics(self):
            return None

        def order_updates(self):
            bot.deal.closing_qty = bot.deal.opening_qty
            bot.deal.current_position_qty = 0
            bot.deal.closing_price = trailing_stop_price or 95
            bot.status = Status.completed
            return bot

        def position_updates(self, **kwargs):
            pytest.fail("completed bot must not run position updates")

    monkeypatch.setattr(
        "streaming.lifecycle.FuturesPosition", FilledProtectiveOrderPosition
    )

    assert lifecycle.process_tick() is bot
    engine.close_all.assert_called_once_with(deal_type=expected_deal_type)
    engine.kucoin_futures_api.get_futures_position.assert_not_called()
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()
