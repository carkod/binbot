from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from kucoin_universal_sdk.model.common import RestError
from pybinbot import BotModel, MarketType, Position, Status
from sqlalchemy import create_engine, inspect, text
from alembic.migration import MigrationContext
from alembic.operations import Operations

from api.alembic.versions import d2e3f4a5b6c7_dynamic_position_sizing as migration
from api.databases.crud.bot_crud import BotTableCrud
from api.databases.crud.paper_trading_crud import PaperTradingTableCrud
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from api.exchange_apis.kucoin.futures.position_sizing import DynamicPositionSizing
from streaming.lifecycle import Lifecycle
from streaming.context_evaluator import LifecycleEvaluation
from streaming.strategies.base import LifecyclePolicy, LifecycleSignal
from sqlmodel import SQLModel, Session
from api.databases.tables.bot_table import BotTable, PaperTradingTable
from api.databases.tables.deal_table import DealTable


def execution(*, short=False, paper=False):
    bot = BotModel(
        pair="XBTUSDTM",
        fiat="USDT",
        market_type=MarketType.FUTURES,
        status=Status.active,
        dynamic_position_sizing=True,
        stop_loss=5,
        take_profit=10,
        trailing_profit=5,
        trailing_deviation=2,
        position=Position.short if short else Position.long,
        deal={"opening_price": 100, "opening_qty": 100, "current_position_qty": 100},
    )
    result = MagicMock(spec=KucoinPositionDeal)
    result.active_bot = bot
    result.controller = MagicMock(spec=PaperTradingTableCrud) if paper else MagicMock()
    result.kucoin_symbol = bot.pair
    result.kucoin_symbol_data = SimpleNamespace(lot_size=1)
    result.symbol_info = SimpleNamespace(futures_leverage=3)
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


@pytest.mark.parametrize("short,price,side", [(False, 95, "sell"), (True, 105, "buy")])
def test_stop_hit_reduces_only_current_position_and_resets_after_fill(
    short, price, side
):
    engine = execution(short=short)
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.return_value.avg_deal_price = price
    assert DynamicPositionSizing(engine).process(price)
    request = api.add_order.call_args.args[0]
    assert request.reduce_only is True
    assert request.side.value == side
    assert request.size == 25
    assert engine.active_bot.deal.current_position_qty == 75
    assert engine.active_bot.deal.opening_qty == 100
    assert engine.active_bot.status == Status.active
    assert engine.active_bot.deal.position_size_reference_price == price
    # Same price after a restart cannot place the same reduction again.
    DynamicPositionSizing(engine).process(price)
    assert api.add_order.call_count == 1


@pytest.mark.parametrize("short,price,side", [(False, 110, "buy"), (True, 90, "sell")])
def test_profit_hit_increases_using_symbol_leverage_and_confirmed_fill(
    short, price, side
):
    engine = execution(short=short)
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.return_value.avg_deal_price = price
    api.get_order_by_client_oid.return_value.filled_size = 10  # terminal partial fill
    DynamicPositionSizing(engine).process(price)
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
    assert DynamicPositionSizing(engine).process(111) is False
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
    assert DynamicPositionSizing(engine).process(111) is False
    assert engine.active_bot.deal.position_size_order is None
    engine = execution()
    api = engine.kucoin_futures_api.futures_order_api
    api.add_order.side_effect = TimeoutError("unknown submission outcome")
    with pytest.raises(TimeoutError):
        DynamicPositionSizing(engine).process(111)
    pending_id = engine.active_bot.deal.position_size_order.client_oid
    api.get_order_by_client_oid.return_value.is_active = True
    DynamicPositionSizing(engine).process(115)
    assert api.add_order.call_count == 1
    assert api.get_order_by_client_oid.call_args.args[0].client_oid == pending_id
    assert engine.active_bot.deal.current_position_qty == 100


def test_active_partial_order_waits_until_terminal_and_counts_actual_fill_once():
    engine = execution()
    api = engine.kucoin_futures_api.futures_order_api
    api.get_order_by_client_oid.return_value.is_active = True
    DynamicPositionSizing(engine).process(95)
    assert engine.active_bot.deal.position_size_reference_price == 100
    assert engine.active_bot.deal.current_position_qty == 100
    api.get_order_by_client_oid.return_value.is_active = False
    api.get_order_by_client_oid.return_value.filled_size = 4
    DynamicPositionSizing(engine).process(94)
    assert api.add_order.call_count == 1
    assert engine.active_bot.deal.current_position_qty == 96
    assert engine.active_bot.deal.position_size_order is None


@pytest.mark.parametrize(
    "qty,pct,lot,expected",
    [(99, 25, 1, 24), (100, 25, 10, 20), (1, 25, 1, 0), (100, 100, 1, 100)],
)
def test_adjustment_rounds_down_to_exchange_lot(qty, pct, lot, expected):
    assert DynamicPositionSizing.adjustment_quantity(qty, pct, lot) == expected


def test_paper_reductions_use_remaining_quantity_and_close_final_lot():
    engine = execution(paper=True)
    DynamicPositionSizing(engine).process(95)
    DynamicPositionSizing(engine).process(90)
    assert [order.qty for order in engine.active_bot.orders] == [25, 18]
    assert engine.active_bot.deal.current_position_qty == 57
    engine.active_bot.deal.current_position_qty = 1
    DynamicPositionSizing(engine).process(80)
    assert engine.active_bot.status == Status.completed
    assert engine.active_bot.deal.current_position_qty == 0
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()


def test_lifecycle_sizing_replaces_full_close_and_strategy_parameter_updates(
    monkeypatch,
):
    engine = execution(paper=True)
    lifecycle = Lifecycle(engine, SimpleNamespace())
    evaluation = MagicMock()
    monkeypatch.setattr(lifecycle, "_evaluate_strategy", evaluation)
    assert lifecycle.exit(95).deal.current_position_qty == 75
    engine.execute_stop_loss.assert_not_called()
    engine.take_profit_order.assert_not_called()
    evaluation.assert_not_called()


def test_pending_intent_serializes_through_bot_crud():
    engine = execution()
    engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.return_value.is_active = True
    DynamicPositionSizing(engine).process(95)
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
    lifecycle = Lifecycle(engine, SimpleNamespace())
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


def test_paper_tick_does_not_replace_simulated_quantity_with_live_position(monkeypatch):
    engine = execution(paper=True)
    base = MagicMock()
    base.kucoin_futures_api.get_mark_price.return_value = 95
    position = MagicMock()
    position.dataframe_ops.return_value = ([], [])
    monkeypatch.setattr(
        "streaming.lifecycle.FuturesPosition", lambda **kwargs: position
    )
    assert Lifecycle(engine, base).process_tick().deal.current_position_qty == 75
    position.order_updates.assert_not_called()
    position.position_updates.assert_not_called()
    base.kucoin_futures_api.get_futures_position.assert_not_called()


def test_paper_trailing_arms_without_fill_and_closes_only_when_crossed(monkeypatch):
    engine = execution(paper=True)
    engine.active_bot.dynamic_position_sizing = False
    engine.active_bot.trailing = True
    engine.active_bot.take_profit = 0
    engine.active_bot.deal.current_position_qty = 75
    engine.active_bot.deal.trailing_stop_loss_price = 108
    KucoinPositionDeal.place_trailing_stop_loss(engine)
    assert not engine.active_bot.orders
    engine.price_precision = 2
    engine._direction_multiplier.return_value = 1
    engine._is_recovery_bot.return_value = False
    engine.current_position_quantity.return_value = 75
    engine.execute_stop_loss.side_effect = lambda **kwargs: (
        KucoinPositionDeal.execute_stop_loss(engine, **kwargs)
    )
    lifecycle = Lifecycle(engine, SimpleNamespace())
    lifecycle.klines = []
    monkeypatch.setattr(
        lifecycle,
        "_evaluate_strategy",
        lambda **kwargs: LifecycleEvaluation(LifecyclePolicy(), LifecycleSignal()),
    )
    lifecycle.exit(109)
    engine.execute_stop_loss.assert_not_called()
    lifecycle.exit(107)
    assert engine.active_bot.status == Status.completed
    assert engine.active_bot.orders[-1].qty == 75
    assert engine.active_bot.orders[-1].deal_type == "trailing_profit"
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()


def test_paper_entry_and_protection_never_submit_live_orders():
    engine = execution(paper=True)
    engine.active_bot.fiat_order_size = 100
    engine.kucoin_futures_api.get_mark_price.return_value = 100
    engine.calculate_contracts.return_value = 3
    KucoinPositionDeal.base_order(engine)
    KucoinPositionDeal.place_stop_loss(engine)
    KucoinPositionDeal.reconcile_exchange_sl(engine)
    engine.active_bot.deal.trailing_stop_loss_price = 105
    KucoinPositionDeal.reconcile_trailing_stop_loss(engine)
    assert engine.active_bot.deal.current_position_qty == 3
    assert engine.active_bot.orders[-1].qty == 3
    engine.compute_available_balance.assert_not_called()
    engine.kucoin_futures_api.futures_order_api.add_order.assert_not_called()
    engine.kucoin_futures_api.get_futures_position.assert_not_called()


@pytest.mark.parametrize("paper", [False, True])
def test_adjustments_and_pending_intent_survive_database_roundtrip(paper):
    engine = execution(paper=paper)
    db = create_engine("sqlite://")
    SQLModel.metadata.create_all(db)
    table_type = PaperTradingTable if paper else BotTable
    with Session(db) as session:
        row = table_type(id=engine.active_bot.id, pair="XBTUSDTM", deal=DealTable())
        session.add(row)
        session.commit()
        engine.controller = (
            PaperTradingTableCrud(session) if paper else BotTableCrud(session)
        )
        if paper:
            DynamicPositionSizing(engine).process(95)
            DynamicPositionSizing(engine).process(90)
            saved = session.get(table_type, engine.active_bot.id)
            hydrated = BotModel.dump_from_table(saved)
            assert len(hydrated.orders) == 2
            assert hydrated.deal.current_position_qty == 57
        else:
            engine.kucoin_futures_api.futures_order_api.get_order_by_client_oid.return_value.is_active = True
            DynamicPositionSizing(engine).process(95)
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
