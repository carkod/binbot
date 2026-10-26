from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from typing import Any, cast

import pytest
from pybinbot import (
    BotBase,
    BotModel,
    ExchangeId,
    DealType,
    MarketType,
    OrderBase,
    OrderModel,
    OrderStatus,
    Position,
    RecoveryBotModel,
    RecoveryParams,
    Status,
)
from sqlmodel import Session, select

from api.databases.crud.bot_crud import BotTableCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.recovery_bot_table import RecoveryBotTable
from api.exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from streaming.futures_position import FuturesPosition
from streaming.base import BaseStreaming
from streaming.lifecycle import Lifecycle


def execution(*, position=Position.long):
    engine = cast(Any, object.__new__(KucoinPositionDeal))
    engine.active_bot = BotModel(
        pair="TESTUSDTM",
        market_type=MarketType.FUTURES,
        position=position,
        status=Status.active,
        stop_loss=2,
    )
    engine.active_bot.deal.opening_qty = 101
    engine.active_bot.deal.current_position_qty = 101
    engine.active_bot.deal.opening_price = 100
    engine.price_precision = 4
    engine.kucoin_symbol = "TESTUSDTM"
    engine.controller = Mock()
    engine.kucoin_futures_api = Mock()
    engine.matching_exchange_fill_timestamp = lambda order, **kwargs: kwargs.get(
        "fallback_timestamp", 0
    )
    return engine


@pytest.mark.parametrize(
    "position,side,stop",
    [(Position.long, "sell", "down"), (Position.short, "buy", "up")],
)
def test_conditional_close_persists_identity_before_submission_and_never_doubles_quantity(
    position, side, stop
):
    engine = execution(position=position)

    def submit(**kwargs):
        assert (
            engine.active_bot.deal.conditional_close_order.client_oid
            == kwargs["client_oid"]
        )
        assert engine.controller.save.called
        assert kwargs["size"] == 101
        assert kwargs["reduce_only"] is True
        assert kwargs["allow_market_fallback"] is False
        assert kwargs["side"].value == side
        assert kwargs["stop"].value == stop
        return OrderBase(
            order_id="close-1",
            order_type="market",
            time_in_force="GTC",
            order_side=side,
            pair="TESTUSDTM",
            price=0,
            qty=0,
            status=OrderStatus.NEW,
            deal_type=DealType.stop_loss,
        )

    engine.kucoin_futures_api.place_futures_order.side_effect = submit
    order = engine.place_conditional_close(
        98 if position == Position.long else 102, 101, DealType.stop_loss
    )
    assert order.price == 0
    assert order.qty == 0
    assert order.requested_qty == 101
    assert order.client_oid is not None
    assert order.stop_price > 0


def test_lost_conditional_acknowledgement_is_adopted_without_second_submission():
    engine = execution()
    engine.kucoin_futures_api.place_futures_order.side_effect = TimeoutError(
        "lost response"
    )
    with pytest.raises(TimeoutError):
        engine.place_conditional_close(98, 101, DealType.stop_loss)
    saved = engine.active_bot.model_dump()
    engine.active_bot = BotModel.model_validate(saved)
    engine.kucoin_futures_api.retrieve_order_by_client_oid.return_value = (
        SimpleNamespace(
            id="accepted-1",
            avg_deal_price=None,
            filled_size=0,
            created_at=10,
            status=SimpleNamespace(value="open"),
        )
    )
    order = engine.place_conditional_close(98, 101, DealType.stop_loss)
    assert order.order_id == "accepted-1"
    assert engine.kucoin_futures_api.place_futures_order.call_count == 1
    engine.kucoin_futures_api.retrieve_order_by_client_oid.assert_called_once_with(
        order.client_oid
    )


def test_completed_source_and_unique_pending_child_are_committed_together(
    create_test_tables,
):
    with Session(create_test_tables) as session:
        crud = BotTableCrud(session)
        source_row = crud.create(
            BotBase(
                pair=f"RECOVERY-{uuid4()}",
                market_type=MarketType.FUTURES,
                recovery_params=RecoveryParams(),
                status=Status.active,
            )
        )
        source = BotModel.dump_from_table(source_row)
        source.deal.closing_qty = 101
        source.deal.closing_price = 98
        source.deal.current_position_qty = 0
        child = BotBase(
            pair=source.pair,
            market_type=MarketType.FUTURES,
            status=Status.pending,
            position=Position.short,
            recovery_params=RecoveryParams(
                reversal_path="recovery",
                source_bot_id=source.id,
                source_close_order_id="stop-1",
                source_contracts=101,
                source_loss_fiat=202,
                stop_loss_pct=3,
            ),
        )
        first = crud.complete_with_recovery(source, child)
        second = crud.complete_with_recovery(source, child)
        assert first.id == second.id
        assert first.status == Status.pending
        stored_source = session.get(BotTable, source.id)
        assert stored_source is not None
        assert stored_source.status == Status.completed
        assert (
            len(
                session.exec(
                    select(RecoveryBotTable).where(
                        RecoveryBotTable.source_bot_id == source.id
                    )
                ).all()
            )
            == 1
        )


def test_child_creation_failure_rolls_back_source_completion(
    create_test_tables, monkeypatch
):
    with Session(create_test_tables) as session:
        crud = BotTableCrud(session)
        row = crud.create(BotBase(pair=f"ROLLBACK-{uuid4()}", status=Status.active))
    source = BotModel.dump_from_table(row)
    source.deal.closing_qty = 1
    source.deal.closing_price = 98
    source.deal.current_position_qty = 0

    def fail_create(self, data):
        raise RuntimeError("child insert failed")

    monkeypatch.setattr(BotTableCrud, "create", fail_create)
    # Use the same test database but an independent transaction owned by the
    # enclosing context, like the streaming worker's transaction.
    with Session(create_test_tables) as session:
        with pytest.raises(RuntimeError):
            try:
                BotTableCrud(session).complete_with_recovery(
                    source, BotBase(pair=source.pair)
                )
            except RuntimeError:
                session.rollback()
                raise
        stored_source = session.get(BotTable, source.id)
        assert stored_source is not None
        assert stored_source.status == Status.active


def test_recovery_and_position_sizing_are_rejected_together():
    with pytest.raises(ValueError, match="mutually exclusive"):
        BotBase(
            pair="TESTUSDTM",
            market_type=MarketType.FUTURES,
            dynamic_position_sizing=True,
            recovery_params=RecoveryParams(),
            stop_loss=2,
            take_profit=2,
            trailing_profit=2,
            trailing_deviation=1,
        )


def reconciler(engine, details):
    engine.kucoin_futures_api.retrieve_order.return_value = details
    engine.kucoin_futures_api.get_futures_position.return_value = SimpleNamespace(
        current_qty=0
    )
    fp = cast(Any, object.__new__(FuturesPosition))
    fp.execution = engine
    fp.base_streaming = SimpleNamespace(
        kucoin_futures_api=engine.kucoin_futures_api,
        exchange=ExchangeId.KUCOIN,
        interval=SimpleNamespace(get_ms=lambda: 900000),
    )
    fp.price_precision = 4
    fp.qty_precision = 0
    return fp


def test_price_only_update_is_saved_and_source_remains_owned_for_recovery():
    engine = execution()
    engine.active_bot.recovery_params = RecoveryBotModel(
        id=uuid4(), created_at=1, updated_at=1
    )
    engine.active_bot.orders = [
        OrderModel(
            order_id="filled-close",
            order_type="market",
            order_side="sell",
            pair="TESTUSDTM",
            time_in_force="GTC",
            timestamp=1,
            price=0,
            qty=101,
            status=OrderStatus.FILLED,
            deal_type=DealType.stop_loss,
        )
    ]
    details = SimpleNamespace(
        status=SimpleNamespace(value="done"),
        filled_size=101,
        avg_deal_price=98,
        price=0,
        created_at=1,
        end_at=50,
        updated_at=50,
        cancel_exist=False,
        remark=None,
    )
    fp = reconciler(engine, details)
    fp.order_updates()
    assert engine.active_bot.orders[0].price == 98
    engine.controller.update_order.assert_called_once()
    assert engine.active_bot.deal.closing_price == 98
    assert engine.active_bot.status == Status.active


def test_flat_position_with_missing_execution_price_stays_tracked_until_history_arrives():
    engine = execution()
    engine.active_bot.orders = [
        OrderModel(
            order_id="late-price",
            order_type="market",
            order_side="sell",
            pair="TESTUSDTM",
            time_in_force="GTC",
            timestamp=1,
            price=0,
            qty=0,
            status=OrderStatus.NEW,
            deal_type=DealType.stop_loss,
        )
    ]
    details = SimpleNamespace(
        status=SimpleNamespace(value="done"),
        filled_size=101,
        avg_deal_price=None,
        price=0,
        created_at=1,
        end_at=50,
        updated_at=50,
        cancel_exist=False,
        remark=None,
    )
    engine.kucoin_futures_api.get_order_execution.side_effect = [
        (101, 0, 0),
        (101, 97.9, 55),
    ]
    fp = reconciler(engine, details)
    fp.order_updates()
    assert engine.active_bot.deal.current_position_qty == 0
    assert engine.active_bot.deal.closing_price == 0
    assert engine.active_bot.status == Status.active
    fp.order_updates()
    assert engine.active_bot.deal.closing_price == pytest.approx(97.9)
    assert engine.active_bot.deal.closing_timestamp == 55
    assert engine.active_bot.status == Status.completed


def test_recovery_child_never_creates_another_recovery():
    engine = execution()
    engine.active_bot.recovery_params = RecoveryBotModel(
        id=uuid4(), created_at=1, updated_at=1, reversal_path="recovery"
    )
    engine.active_bot.deal.current_position_qty = 0
    engine.active_bot.deal.closing_qty = 101
    engine.active_bot.deal.closing_price = 98
    lifecycle = Lifecycle(
        engine,
        cast(
            BaseStreaming,
            SimpleNamespace(interval=SimpleNamespace(get_ms=lambda: 900000)),
        ),
    )
    lifecycle.recover_closed_position()
    assert engine.active_bot.status == Status.completed
    engine.controller.complete_with_recovery.assert_not_called()


def test_complete_native_fill_rechecks_lagging_position_before_handoff():
    engine = execution()
    engine.active_bot.recovery_params = RecoveryBotModel(
        id=uuid4(), created_at=1, updated_at=1
    )
    engine.active_bot.orders = [
        OrderModel(
            order_id="lagging-position",
            order_type="market",
            order_side="sell",
            pair="TESTUSDTM",
            time_in_force="GTC",
            timestamp=1,
            price=0,
            qty=0,
            requested_qty=101,
            status=OrderStatus.NEW,
            deal_type=DealType.stop_loss,
        )
    ]
    details = SimpleNamespace(
        status=SimpleNamespace(value="done"),
        filled_size=101,
        avg_deal_price=98,
        price=0,
        created_at=1,
        end_at=50,
        updated_at=50,
        cancel_exist=False,
        remark=None,
    )
    fp = reconciler(engine, details)
    engine.kucoin_futures_api.get_futures_position.side_effect = [
        SimpleNamespace(current_qty=101),
        SimpleNamespace(current_qty=0),
    ]
    fp.order_updates()
    assert engine.active_bot.deal.closing_qty == 0
    assert engine.awaiting_close_confirmation()
    engine.kucoin_futures_api.place_futures_order.assert_not_called()
    fp.order_updates()
    assert engine.active_bot.deal.closing_qty == 101
    assert engine.active_bot.deal.closing_price == 98
    assert engine.active_bot.status == Status.active


@pytest.mark.parametrize("name", ["terminal", "top_gainer_short"])
@pytest.mark.parametrize("fill_price", [0, 98])
def test_persisted_full_fill_respects_recovery_policy_after_worker_restart(
    create_test_tables, monkeypatch, name, fill_price
):
    with Session(create_test_tables) as session:
        crud = BotTableCrud(session)
        row = crud.create(
            BotBase(
                pair=f"CRASH-{uuid4()}",
                name=name,
                market_type=MarketType.FUTURES,
                status=Status.active,
                recovery_params=RecoveryParams(),
            )
        )
        engine = execution()
        engine.active_bot = BotModel.dump_from_table(row)
        engine.active_bot.deal.opening_price = 100
        engine.active_bot.deal.opening_qty = 101
        engine.active_bot.deal.current_position_qty = 101
        engine.active_bot.orders = [
            OrderModel(
                order_id=f"close-{uuid4()}",
                pair=row.pair,
                order_type="market",
                order_side="sell",
                time_in_force="GTC",
                status=OrderStatus.NEW,
                price=0,
                qty=0,
                requested_qty=101,
                deal_type=DealType.stop_loss,
            )
        ]
        crud.save(engine.active_bot)
        engine.controller = crud
        details = SimpleNamespace(
            status=SimpleNamespace(value="done"),
            filled_size=101,
            avg_deal_price=fill_price,
            price=0,
            created_at=1,
            end_at=50,
            updated_at=50,
            cancel_exist=False,
            remark=None,
        )
        fp = reconciler(engine, details)
        engine.kucoin_futures_api.get_order_execution.return_value = (
            101,
            fill_price,
            50,
        )
        engine.kucoin_futures_api.get_futures_position.return_value = None
        update_order = crud.update_order

        def commit_order_then_stop(order):
            update_order(order)
            raise RuntimeError("Worker stopped after order commit")

        monkeypatch.setattr(crud, "update_order", commit_order_then_stop)
        with pytest.raises(RuntimeError, match="Worker stopped"):
            fp.order_updates()
        monkeypatch.setattr(crud, "update_order", update_order)

        # Restart from the database: the order is filled but the deal still
        # shows all 101 contracts, so there is no new fill delta to apply.
        engine.active_bot = BotModel.dump_from_table(crud.get_one(bot_id=str(row.id)))
        assert engine.active_bot.orders[0].qty == 101
        assert engine.active_bot.deal.current_position_qty == 101
        fp.order_updates()
        assert engine.active_bot.deal.current_position_qty == 0
        assert engine.active_bot.deal.closing_qty == 101
        assert engine.active_bot.status == Status.active
        if fill_price == 0:
            assert engine.active_bot.deal.closing_price == 0
            engine.kucoin_futures_api.get_order_execution.return_value = (101, 98, 50)
            fp.order_updates()
        assert engine.active_bot.deal.closing_price == 98

        engine.kucoin_symbol_data = SimpleNamespace(multiplier=1)
        lifecycle = Lifecycle(
            engine,
            cast(
                BaseStreaming,
                SimpleNamespace(interval=SimpleNamespace(get_ms=lambda: 900000)),
            ),
        )
        monkeypatch.setattr(
            lifecycle, "compute_recovery_stop_loss_pct", lambda *args: 3
        )
        monkeypatch.setattr(
            "streaming.lifecycle.AutotradeCrud",
            lambda: SimpleNamespace(
                get_settings=lambda: SimpleNamespace(base_order_size=20)
            ),
        )
        result = lifecycle.exit(98)
        if name == "top_gainer_short":
            assert result.id == row.id
            assert result.status == Status.completed
            assert result.position == Position.long
        else:
            assert result.status == Status.pending
            assert result.position == Position.short
            assert result.recovery_params is not None
            assert result.recovery_params.source_bot_id == row.id


def test_repeated_cumulative_partial_close_does_not_reduce_remaining_quantity_twice():
    engine = execution()
    engine.active_bot.orders = [
        OrderModel(
            order_id="partial-close",
            order_type="market",
            order_side="sell",
            pair="TESTUSDTM",
            time_in_force="GTC",
            timestamp=1,
            price=0,
            qty=0,
            requested_qty=101,
            status=OrderStatus.NEW,
            deal_type=DealType.stop_loss,
        )
    ]
    details = SimpleNamespace(
        status=SimpleNamespace(value="match"),
        filled_size=40,
        avg_deal_price=98,
        price=0,
        created_at=1,
        end_at=50,
        updated_at=50,
        cancel_exist=False,
        remark=None,
    )
    fp = reconciler(engine, details)
    engine.kucoin_futures_api.get_futures_position.return_value = None
    fp.order_updates()
    assert engine.active_bot.deal.current_position_qty == 61
    fp.order_updates()
    assert engine.active_bot.deal.current_position_qty == 61
    assert engine.active_bot.deal.closing_qty == 0
    # A delayed snapshot cannot shrink the cumulative execution and make
    # the same 40 contracts count again on the next current snapshot.
    details.filled_size = 20
    fp.order_updates()
    assert engine.active_bot.orders[0].qty == 40
    details.filled_size = 40
    fp.order_updates()
    assert engine.active_bot.deal.current_position_qty == 61
    details.filled_size = 80
    fp.order_updates()
    fp.order_updates()
    assert engine.active_bot.deal.current_position_qty == 21
    assert engine.active_bot.deal.closing_qty == 0


def test_unacknowledged_conditional_retry_preserves_client_oid_and_original_trigger(
    monkeypatch,
):
    from kucoin_universal_sdk.model.common import RestError

    engine = execution()
    engine.kucoin_futures_api.place_futures_order.side_effect = TimeoutError(
        "no acknowledgement"
    )
    with pytest.raises(TimeoutError):
        engine.place_conditional_close(98, 101, DealType.stop_loss)
    intent = engine.active_bot.deal.conditional_close_order
    original_id = intent.client_oid
    intent.not_found_count = 2
    intent.not_found_since_ms = 1
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.futures_deal.time", lambda: 100
    )
    engine.kucoin_futures_api.retrieve_order_by_client_oid.side_effect = RestError(
        msg="missing",
        response=SimpleNamespace(code=100001, message="error.getOrder.orderNotExist"),
    )
    engine.kucoin_futures_api.place_futures_order.side_effect = None
    engine.kucoin_futures_api.place_futures_order.return_value = OrderBase(
        order_id="retried",
        order_type="market",
        order_side="sell",
        pair="TESTUSDTM",
        time_in_force="GTC",
        price=0,
        qty=0,
        status=OrderStatus.NEW,
        deal_type=DealType.stop_loss,
    )
    engine.place_conditional_close(95, 42, DealType.stop_loss)
    req = engine.kucoin_futures_api.place_futures_order.call_args.kwargs
    assert req["client_oid"] == original_id
    assert req["stop_price"] == 98
    assert req["size"] == 101
    assert req["reduce_only"] is True
    assert req["allow_market_fallback"] is False


def test_confirmed_native_close_creates_opposite_pending_bot_then_uses_normal_entry(
    create_test_tables, monkeypatch
):
    with Session(create_test_tables) as session:
        crud = BotTableCrud(session)
        row = crud.create(
            BotBase(
                pair=f"LINKED-{uuid4()}",
                fiat="USDT",
                market_type=MarketType.FUTURES,
                status=Status.active,
                recovery_params=RecoveryParams(),
            )
        )
        engine = execution()
        engine.active_bot = BotModel.dump_from_table(row)
        engine.active_bot.deal.opening_price = 100
        engine.active_bot.deal.closing_price = 98
        engine.active_bot.deal.closing_qty = 101
        engine.active_bot.deal.current_position_qty = 0
        engine.active_bot.orders = [
            OrderModel(
                order_id="confirmed-native-close",
                order_type="market",
                order_side="sell",
                pair=engine.active_bot.pair,
                time_in_force="GTC",
                price=98,
                qty=101,
                status=OrderStatus.FILLED,
                deal_type=DealType.stop_loss,
            )
        ]
        engine.controller = crud
        engine.kucoin_symbol_data = SimpleNamespace(multiplier=1)
        lifecycle = Lifecycle(
            engine,
            cast(
                BaseStreaming,
                SimpleNamespace(interval=SimpleNamespace(get_ms=lambda: 900000)),
            ),
        )
        monkeypatch.setattr(
            lifecycle,
            "compute_recovery_stop_loss_pct",
            lambda reference_price, target_position: 3,
        )
        monkeypatch.setattr(
            "streaming.lifecycle.AutotradeCrud",
            lambda: SimpleNamespace(
                get_settings=lambda: SimpleNamespace(base_order_size=20)
            ),
        )
        child = lifecycle.exit(98)
        assert child.status == Status.pending
        assert child.position == Position.short
        assert child.recovery_params is not None
        assert child.recovery_params.source_bot_id == row.id
        assert child.recovery_params.source_close_order_id == "confirmed-native-close"
        assert child.dynamic_position_sizing is False
        assert child.orders == []
        engine.open_deal = Mock(return_value=child)
        lifecycle.exit(98)
        engine.open_deal.assert_called_once()
