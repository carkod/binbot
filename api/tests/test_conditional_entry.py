from contextlib import contextmanager, nullcontext
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import Request
from pybinbot import (
    BinbotErrors,
    BotModel,
    DealType,
    EntryMode,
    ExchangeId,
    MarketType,
    OrderBase,
    OrderStatus,
    Position,
    Status,
)
from sqlmodel import Session, SQLModel, create_engine

from api.bots.routes import activate_bot
from api.databases.crud.bot_crud import BotTableCrud
from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable
from api.deals.conditional_entry import (
    ConditionalEntry,
    ConditionalEntryClosed,
    EntryCapacityError,
)
from .test_kucoin_futures_contract_sizing import make_sizing_deal
from streaming.futures_position import FuturesPosition
from streaming.lifecycle import Lifecycle


@pytest.fixture
def conditional_deal(monkeypatch):
    execution = make_sizing_deal(fiat_order_size=100, multiplier=1)
    bot = execution.active_bot
    bot.market_type = MarketType.FUTURES
    bot.entry_mode = EntryMode.conditional_limit
    bot.entry_price = 10
    bot.entry_expires_at = 100_000
    bot.status = Status.pending
    execution.fiat = "USDT"
    execution.kucoin_symbol_data.tick_size = 0.1
    execution.controller = SimpleNamespace(
        save=Mock(), delete=Mock(), update_logs=Mock()
    )
    execution.body_capped_entry_limit_price = Mock(
        side_effect=AssertionError("Explicit limit must be preserved")
    )
    execution.prepare_entry_limit_price = Mock(
        side_effect=AssertionError("Explicit limit must not be repriced")
    )
    execution.kucoin_futures_api.place_futures_order = Mock(
        return_value=OrderBase(
            order_id="entry",
            pair=bot.pair,
            order_type="limit",
            order_side="sell",
            qty=9,
            price=0,
            timestamp=2000,
            time_in_force="GTC",
            status=OrderStatus.NEW,
            deal_type=DealType.base_order,
        )
    )
    session = Mock()
    session.exec.return_value.one.return_value = 0
    monkeypatch.setattr(
        "api.deals.conditional_entry.submission_guard",
        lambda _bot_id: nullcontext((bot, session)),
    )
    monkeypatch.setattr(
        "api.deals.conditional_entry.AutotradeCrud",
        lambda _session: SimpleNamespace(
            get_settings=lambda: SimpleNamespace(max_active_autotrade_bots=10)
        ),
    )
    monkeypatch.setattr("api.deals.conditional_entry.timestamp", lambda: 2000)
    book = SimpleNamespace(
        bids=[SimpleNamespace(price=10.1)],
        asks=[SimpleNamespace(price=10.2)],
        exchange_timestamp_ms=2000,
    )
    monkeypatch.setattr(
        "api.deals.conditional_entry.load_futures_order_book",
        lambda *args: book,
    )
    balance = Mock(return_value=({}, 100, 100))
    monkeypatch.setattr(
        "api.deals.conditional_entry.KucoinFuturesBalance",
        lambda: SimpleNamespace(compute_futures_balance=balance),
    )
    return execution, book, balance


@pytest.mark.parametrize(
    "position, price, expected",
    [(Position.short, 10.01, 10.1), (Position.long, 10.29, 10.2)],
)
def test_trigger_submits_limit_rounded_without_worsening_price(
    conditional_deal, position, price, expected
):
    execution, _, _ = conditional_deal
    execution.active_bot.position = position
    execution.active_bot.entry_price = price
    result = execution.open_deal(trigger_entry=True)
    args = execution.kucoin_futures_api.place_futures_order.call_args.kwargs
    assert args["price"] == expected
    assert args["post_only"] is False
    assert args["client_oid"] == result.deal.entry_client_oid
    assert execution.required_margin_for_contracts(args["size"], args["price"]) <= 100
    assert result.status == Status.pending


def test_price_not_reached_does_not_spend_or_check_funds(conditional_deal):
    execution, _, balance = conditional_deal
    execution.active_bot.entry_price = 11
    execution.open_deal(trigger_entry=True)
    execution.kucoin_futures_api.place_futures_order.assert_not_called()
    balance.assert_not_called()


def test_manual_activation_arms_without_submitting(conditional_deal):
    execution, _, balance = conditional_deal
    execution.active_bot.status = Status.inactive
    result = execution.open_deal()
    assert result.status == Status.pending
    execution.kucoin_futures_api.place_futures_order.assert_not_called()
    balance.assert_not_called()


@pytest.mark.parametrize("trigger_entry", [False, True])
def test_closed_candidate_cannot_be_reactivated(conditional_deal, trigger_entry):
    execution, _, balance = conditional_deal
    execution.active_bot.status = Status.closed
    result = execution.open_deal(trigger_entry=trigger_entry)
    assert result.status == Status.closed
    execution.controller.save.assert_not_called()
    execution.kucoin_futures_api.place_futures_order.assert_not_called()
    balance.assert_not_called()


def test_closed_candidate_is_not_processed_by_streaming(conditional_deal):
    execution, _, balance = conditional_deal
    execution.active_bot.status = Status.closed
    lifecycle = Lifecycle.__new__(Lifecycle)
    lifecycle.execution = execution
    assert lifecycle.process_tick() is execution.active_bot
    execution.controller.save.assert_not_called()
    balance.assert_not_called()


def test_insufficient_funds_archives_unsubmitted_candidate(conditional_deal):
    execution, _, balance = conditional_deal
    balance.return_value = ({}, 0, 0)
    with pytest.raises(ConditionalEntryClosed):
        execution.open_deal(trigger_entry=True)
    execution.controller.delete.assert_not_called()
    execution.controller.save.assert_called_once_with(execution.active_bot)
    assert execution.active_bot.status == Status.closed
    assert execution.active_bot.deal.entry_client_oid is None
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


@pytest.mark.parametrize("trigger_entry", [False, True])
def test_expired_candidate_is_closed_without_submission(
    conditional_deal, trigger_entry
):
    execution, _, balance = conditional_deal
    execution.active_bot.entry_expires_at = 2000
    with pytest.raises(ConditionalEntryClosed, match="expired before"):
        execution.open_deal(trigger_entry=trigger_entry)
    execution.controller.delete.assert_not_called()
    execution.controller.save.assert_called_once_with(execution.active_bot)
    assert execution.active_bot.status == Status.closed
    balance.assert_not_called()
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


def test_candidate_expiring_during_sizing_is_closed_before_submission(
    conditional_deal, monkeypatch
):
    execution, _, balance = conditional_deal
    times = iter([2000, 2000, 2000, 100_000])
    monkeypatch.setattr("api.deals.conditional_entry.timestamp", lambda: next(times))
    with pytest.raises(ConditionalEntryClosed, match="expired before submission"):
        execution.open_deal(trigger_entry=True)
    balance.assert_called_once()
    execution.controller.delete.assert_not_called()
    execution.controller.save.assert_called_once_with(execution.active_bot)
    assert execution.active_bot.status == Status.closed
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


def test_lifecycle_returns_persisted_closed_candidate(conditional_deal):
    execution, _, _ = conditional_deal
    execution.active_bot.entry_expires_at = 2000
    lifecycle = Lifecycle.__new__(Lifecycle)
    lifecycle.execution = execution
    result = lifecycle.process_tick()
    assert result.status == Status.closed
    execution.controller.delete.assert_not_called()
    execution.controller.save.assert_called_once_with(result)


def test_stale_quote_does_not_trigger(conditional_deal):
    execution, book, balance = conditional_deal
    book.exchange_timestamp_ms = -4000
    with pytest.raises(Exception, match="fresh order book"):
        execution.open_deal(trigger_entry=True)
    balance.assert_not_called()


@pytest.mark.parametrize(
    "original_mode, persisted_mode",
    [
        (EntryMode.immediate, EntryMode.conditional_limit),
        (EntryMode.conditional_limit, EntryMode.immediate),
    ],
)
def test_mode_changed_after_dispatch_never_submits_using_the_stale_workflow(
    conditional_deal, monkeypatch, original_mode, persisted_mode
):
    execution, _, balance = conditional_deal
    execution.active_bot.entry_mode = original_mode
    persisted = execution.active_bot.model_copy(deep=True)
    persisted.entry_mode = persisted_mode
    monkeypatch.setattr(
        "api.exchange_apis.kucoin.futures.futures_deal.submission_guard",
        lambda _bot_id: nullcontext((persisted, None)),
    )
    monkeypatch.setattr(
        ConditionalEntry, "entry_submission", lambda self: nullcontext(persisted)
    )

    result = execution.base_order()

    assert result is persisted
    balance.assert_not_called()
    execution.body_capped_entry_limit_price.assert_not_called()
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


def test_conditional_pending_never_uses_immediate_exit_activation(conditional_deal):
    execution, _, _ = conditional_deal
    execution.awaiting_close_confirmation = lambda: False
    execution.open_deal = Mock()
    lifecycle = Lifecycle.__new__(Lifecycle)
    lifecycle.execution = execution
    lifecycle.exit(10)
    execution.open_deal.assert_not_called()


def test_expiry_uses_absolute_deadline_after_submission(conditional_deal):
    execution, _, _ = conditional_deal
    execution.open_deal(trigger_entry=True)
    position = FuturesPosition.__new__(FuturesPosition)
    position.execution = execution
    order = execution.active_bot.orders[0]
    assert not position.is_pending_base_entry_expired(order, 99_999)
    assert position.is_pending_base_entry_expired(order, 100_000)
    execution.active_bot.status = Status.active
    assert not position.is_pending_base_entry_expired(order, 100_000)


def test_expiry_retains_bot_when_cancellation_finds_exposure(
    conditional_deal, monkeypatch
):
    execution, _, _ = conditional_deal
    execution.open_deal(trigger_entry=True)
    position = FuturesPosition.__new__(FuturesPosition)
    position.execution = execution
    monkeypatch.setattr(
        position, "_cancel_pending_entry_and_confirm_unfilled", Mock(return_value=False)
    )
    position._expire_unfilled_base_order(
        execution.active_bot.orders[0], execution.kucoin_symbol
    )
    assert execution.active_bot.status == Status.pending
    execution.controller.delete.assert_not_called()


@pytest.mark.parametrize(
    "exchange_status, filled_size, fill_price, position_qty, actual_fill, closed",
    [
        (OrderStatus.CANCELED, 0, 0, 0, (0, 0), True),
        (OrderStatus.CANCELED, 2, 10, 2, (2, 10), False),
        (OrderStatus.CANCELED, 2, 0, 0, (0, 0), False),
        (OrderStatus.CANCELED, 0, 0, 0, (2, 0), False),
        (OrderStatus.CANCELED, 0, 0, 2, (0, 0), False),
        (OrderStatus.NEW, 0, 0, 0, (0, 0), False),
        (None, 0, 0, 0, (0, 0), False),
    ],
)
def test_submitted_expiry_closes_only_after_confirming_no_fills_or_position(
    conditional_deal,
    monkeypatch,
    exchange_status,
    filled_size,
    fill_price,
    position_qty,
    actual_fill,
    closed,
):
    execution, _, _ = conditional_deal
    execution.open_deal(trigger_entry=True)
    execution.controller.save.reset_mock()
    execution.controller.update_order = Mock()
    execution._actual_fill = Mock(return_value=actual_fill)
    position = FuturesPosition.__new__(FuturesPosition)
    position.execution = execution
    position.price_precision = 2
    position.qty_precision = 0
    api = Mock()
    monkeypatch.setattr(
        position,
        "base_streaming",
        SimpleNamespace(kucoin_futures_api=api),
        raising=False,
    )
    order = execution.active_bot.orders[0]
    refreshed = (
        SimpleNamespace(
            status=SimpleNamespace(value=exchange_status.value),
            filled_size=filled_size,
            avg_deal_price=fill_price,
            price=10,
            created_at=2000,
        )
        if exchange_status
        else None
    )
    monkeypatch.setattr(
        position, "_retrieve_order_or_none", Mock(return_value=refreshed)
    )
    monkeypatch.setattr(
        position, "_absolute_position_qty", Mock(return_value=position_qty)
    )
    monkeypatch.setattr(
        OrderStatus, "map_from_kucoin_status", staticmethod(OrderStatus)
    )
    activate = Mock()
    monkeypatch.setattr(position, "_activate_filled_base_order", activate)

    position._expire_unfilled_base_order(order, execution.kucoin_symbol)

    api.cancel_futures_order.assert_called_once_with(str(order.order_id))
    if closed:
        execution.controller.delete.assert_not_called()
        execution.controller.save.assert_called_once_with(execution.active_bot)
        assert execution.active_bot.status == Status.closed
        assert order.status == OrderStatus.EXPIRED
        assert order.qty == 0
        assert any(
            "Closed expired conditional bot" in log for log in execution.active_bot.logs
        )
    else:
        execution.controller.delete.assert_not_called()
    if (filled_size > 0 and fill_price <= 0) or (
        actual_fill[0] > 0 and actual_fill[1] <= 0
    ):
        assert any(
            "unresolved price; retaining bot" in log
            for log in execution.active_bot.logs
        )
        execution.controller.save.assert_called_once_with(execution.active_bot)
    if filled_size > 0 and fill_price > 0:
        activate.assert_called_once()
    else:
        activate.assert_not_called()


def test_unresolved_entry_fill_is_saved_in_bot_logs(
    conditional_deal, monkeypatch, caplog
):
    execution, _, _ = conditional_deal
    execution.open_deal(trigger_entry=True)
    execution.controller.save.reset_mock()
    execution._actual_fill = Mock(return_value=(2, 0))
    position = FuturesPosition.__new__(FuturesPosition)
    position.execution = execution
    monkeypatch.setattr(position, "backfill_missing_stop_loss", Mock())
    api = Mock()
    api.retrieve_order.return_value = SimpleNamespace(
        status=SimpleNamespace(value=OrderStatus.CANCELED.value),
        filled_size=0,
        avg_deal_price=0,
        remark=None,
    )
    monkeypatch.setattr(
        position,
        "base_streaming",
        SimpleNamespace(
            exchange=ExchangeId.KUCOIN,
            interval=SimpleNamespace(get_ms=lambda: 900_000),
            kucoin_futures_api=api,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        "streaming.futures_position.convert_to_kucoin_symbol",
        lambda _bot: execution.kucoin_symbol,
    )
    monkeypatch.setattr(
        OrderStatus, "map_from_kucoin_status", staticmethod(OrderStatus)
    )

    position.order_updates()

    assert any(
        "Entry order entry has fills with an unresolved price" in log
        for log in execution.active_bot.logs
    )
    execution.controller.save.assert_called_once_with(execution.active_bot)
    execution.controller.delete.assert_not_called()
    assert not any("unresolved price" in record.message for record in caplog.records)


@pytest.mark.parametrize("concurrent", [False, True])
def test_waiting_candidates_do_not_take_slots_but_submitted_entries_do(
    monkeypatch, tmp_path, concurrent
):
    engine = create_engine(f"sqlite:///{tmp_path / 'entries.db'}")
    SQLModel.metadata.create_all(engine)
    candidates = [
        BotTable(
            pair=f"COIN{i}USDTM",
            entry_mode="conditional_limit",
            entry_price=10,
            market_type=MarketType.FUTURES,
            status=Status.pending,
            deal=DealTable(),
        )
        for i in range(3)
    ]
    with Session(engine) as session:
        session.add_all(candidates)
        session.commit()
        ids = [bot.id for bot in candidates]

    @contextmanager
    def database_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr("api.tools.utils.get_db_session", database_session)
    monkeypatch.setattr(
        "api.deals.conditional_entry.AutotradeCrud",
        lambda session: SimpleNamespace(
            get_settings=lambda: SimpleNamespace(max_active_autotrade_bots=2)
        ),
    )
    barrier = Barrier(3) if concurrent else None

    def submit(bot_id):
        assert bot_id is not None
        if barrier is not None:
            barrier.wait(timeout=5)
        try:
            conditional_entry = ConditionalEntry(
                Mock(active_bot=SimpleNamespace(id=bot_id))
            )
            with conditional_entry.entry_submission() as bot:
                with Session(engine) as session:
                    row = session.get(DealTable, candidates[ids.index(bot_id)].deal_id)
                    assert row is not None
                    row.entry_client_oid = str(bot.id)
                    session.add(row)
                    session.commit()
            return True
        except EntryCapacityError:
            return False

    if concurrent:
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(submit, ids))
    else:
        results = [submit(bot_id) for bot_id in ids]
    assert results.count(True) == 2
    assert results.count(False) == 1


def test_repeated_trigger_adopts_submitted_order_without_spending_twice(
    conditional_deal,
):
    execution, _, balance = conditional_deal
    execution.open_deal(trigger_entry=True)
    execution.base_order()
    execution.kucoin_futures_api.place_futures_order.assert_called_once()
    balance.assert_called_once()


def test_stale_worker_does_not_activate_a_disarmed_candidate(conditional_deal):
    execution, _, balance = conditional_deal
    execution.active_bot.status = Status.inactive
    result = execution.open_deal(trigger_entry=True)
    assert result.status == Status.inactive
    balance.assert_not_called()
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


@pytest.mark.parametrize(
    "failure, expected",
    [
        ("price", "Conditional entry requires an entry price"),
        ("book", "Conditional entry requires a fresh order book"),
        ("size", "Fiat order size must be set."),
        ("capacity", "Waiting for an available bot slot"),
        ("margin", "Insufficient margin including fees"),
    ],
)
def test_submission_failures_are_timestamped_persisted_and_still_abort(
    conditional_deal, monkeypatch, failure, expected
):
    execution, book, _ = conditional_deal
    if failure == "price":
        execution.active_bot.entry_price = None
    elif failure == "book":
        book.exchange_timestamp_ms = -4000
    elif failure == "size":
        execution.active_bot.fiat_order_size = 0
    elif failure == "capacity":
        monkeypatch.setattr(
            "api.deals.conditional_entry.AutotradeCrud",
            lambda _session: SimpleNamespace(
                get_settings=lambda: SimpleNamespace(max_active_autotrade_bots=0)
            ),
        )
    else:
        execution.validate_entry_margin = Mock(side_effect=BinbotErrors(expected))

    with pytest.raises(BinbotErrors, match=expected):
        execution.open_deal(trigger_entry=True)

    bot = execution.active_bot
    message = f"Conditional entry deferred: {expected}"
    assert bot.logs[-1].startswith("[")
    assert bot.logs[-1].partition("] ")[2] == message
    execution.controller.update_logs.assert_called_once_with(
        log_message=message, bot=bot
    )
    execution.controller.save.assert_not_called()
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


def test_repeated_streaming_failure_returns_refreshed_bot_without_repeating_log(
    conditional_deal,
):
    execution, book, _ = conditional_deal
    persisted_bot = execution.active_bot
    execution.active_bot = persisted_bot.model_copy(deep=True)
    book.exchange_timestamp_ms = -4000
    lifecycle = Lifecycle.__new__(Lifecycle)
    lifecycle.execution = execution

    first = lifecycle.process_tick()
    second = lifecycle.process_tick()

    assert first is persisted_bot
    assert second is persisted_bot
    assert first.status == Status.pending
    assert sum("Conditional entry deferred:" in log for log in second.logs) == 1
    execution.controller.update_logs.assert_called_once()
    execution.kucoin_futures_api.place_futures_order.assert_not_called()


@pytest.mark.parametrize("trigger_entry", [False, True])
def test_deleted_candidate_keeps_timestamped_reason_without_being_saved(
    conditional_deal, trigger_entry
):
    execution, _, _ = conditional_deal
    execution.active_bot.entry_expires_at = 2000
    with pytest.raises(ConditionalEntryClosed):
        execution.open_deal(trigger_entry=trigger_entry)
    assert execution.active_bot.logs[-1].startswith("[")
    assert "Conditional entry deleted: expired before" in execution.active_bot.logs[-1]
    execution.controller.update_logs.assert_not_called()
    execution.controller.save.assert_not_called()


def test_log_persistence_failure_does_not_hide_submission_failure(conditional_deal):
    execution, book, _ = conditional_deal
    book.exchange_timestamp_ms = -4000
    execution.controller.update_logs.side_effect = RuntimeError("Database unavailable")
    with pytest.raises(BinbotErrors, match="fresh order book"):
        execution.open_deal(trigger_entry=True)
    assert "fresh order book" in execution.active_bot.logs[-1]


def test_failure_log_survives_exception_without_overwriting_bot_state(
    conditional_deal, monkeypatch
):
    execution, book, _ = conditional_deal
    bot = execution.active_bot
    book.exchange_timestamp_ms = -4000
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            BotTable(
                id=bot.id,
                pair=bot.pair,
                market_type=MarketType.FUTURES,
                status=Status.inactive,
                entry_price=99,
                deal=DealTable(),
                logs=["Existing message"],
            )
        )
        session.commit()
    monkeypatch.setattr(
        "api.databases.crud.bot_crud.get_db_session",
        lambda _session=None: Session(engine),
    )
    execution.controller = BotTableCrud()

    with pytest.raises(BinbotErrors, match="fresh order book"):
        execution.open_deal(trigger_entry=True)

    with Session(engine) as session:
        row = session.get(BotTable, bot.id)
        assert row is not None
        assert row.status == Status.inactive
        assert row.entry_price == 99
        assert len(row.logs) == 2
        assert row.logs[0] == "Existing message"
        assert row.logs[1].partition("] ")[2] == (
            "Conditional entry deferred: Conditional entry requires a fresh order book"
        )
    engine.dispose()


def test_activation_returns_current_conditional_failure_logs_without_double_logging(
    conditional_deal, monkeypatch
):
    execution, book, _ = conditional_deal
    book.exchange_timestamp_ms = -4000
    loaded_bot = execution.active_bot.model_copy(deep=True)
    monkeypatch.setattr(
        "api.bots.routes.BotTableCrud",
        lambda _session: SimpleNamespace(get_one=lambda **kwargs: loaded_bot),
    )
    monkeypatch.setattr(BotModel, "dump_from_table", staticmethod(lambda row: row))
    gateway = SimpleNamespace(
        deal=execution,
        open_deal=lambda **kwargs: execution.open_deal(trigger_entry=True),
        update_logs=Mock(),
    )
    monkeypatch.setattr("api.bots.routes.DealGateway", lambda *args, **kwargs: gateway)

    with Session() as session:
        response = activate_bot(
            str(loaded_bot.id),
            Request({"type": "http", "headers": []}),
            session=session,
        )

    assert response.error == 1
    assert response.data is execution.active_bot
    assert "fresh order book" in response.data.logs[-1]
    execution.controller.update_logs.assert_called_once()
    gateway.update_logs.assert_not_called()
