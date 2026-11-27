from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlmodel import Session, delete, select

import api.databases.crud.top_gainers_losers_series_crud as movers_crud
from api.charts.models import FastestMoverEntry, FastestMoversSnapshot
from api.databases.crud.top_gainers_losers_series_crud import TopGainersLosersSeriesCrud
from api.databases.tables.futures_price_sample_table import FuturesPriceSampleTable
from api.databases.tables.top_gainers_losers_series_table import (
    TopGainersLosersSeriesTable,
)

SNAPSHOT_AT = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    clock = Mock(wraps=datetime)
    clock.now.return_value = SNAPSHOT_AT + timedelta(minutes=2)
    monkeypatch.setattr(movers_crud, "datetime", clock)
    return clock


@pytest.fixture(autouse=True)
def delivery(monkeypatch):
    send = Mock(return_value=True)
    monkeypatch.setattr(
        movers_crud,
        "TelegramDelivery",
        Mock(return_value=SimpleNamespace(send_once=send)),
    )
    return send


def snapshot(at=SNAPSHOT_AT, rising=(), falling=()):
    def entries(symbols, change):
        return [
            FastestMoverEntry(
                symbol=symbol,
                price_change_1h_percent=change,
                price_change_3h_percent=change * 2,
                price_change_percent=99,
                last_price=100,
                turnover_24h=100000,
            )
            for symbol in symbols
        ]

    return FastestMoversSnapshot(
        source="kucoin_futures",
        recorded_at=at,
        comparison_at=at - timedelta(hours=1),
        gainers=entries(rising, 5),
        losers=entries(falling, -5),
    )


def test_unchanged_membership_is_quiet_even_when_ranks_change(delivery):
    previous = snapshot(SNAPSHOT_AT - timedelta(minutes=30), ("A", "B"), ("C",))
    current = snapshot(rising=("B", "A"), falling=("C",))
    TopGainersLosersSeriesCrud.notify_fastest_movers(previous, current, "test")
    delivery.assert_not_called()


def test_only_new_rising_and_falling_members_are_notified(delivery):
    previous = snapshot(SNAPSHOT_AT - timedelta(minutes=30), ("A",), ("C",))
    current = snapshot(rising=("A", "B"), falling=("C", "D"))
    TopGainersLosersSeriesCrud.notify_fastest_movers(previous, current, "test")
    assert delivery.call_count == 2
    rising, falling = [call.args[0] for call in delivery.call_args_list]
    assert "#B" in rising
    assert "Event: entered Rising" in rising
    assert "Rank: 2" in rising
    assert "1h price change: +5.00%" in rising
    assert "3h price change: +10.00%" in rising
    assert "#D" in falling
    assert "Event: entered Falling" in falling


def test_switching_sides_is_a_new_entry(delivery):
    previous = snapshot(SNAPSHOT_AT - timedelta(minutes=30), rising=("A",))
    TopGainersLosersSeriesCrud.notify_fastest_movers(
        previous, snapshot(falling=("A",)), "test"
    )
    delivery.assert_called_once()
    assert "entered Falling" in delivery.call_args.args[0]


def test_reentry_notifies_after_a_snapshot_outside_the_list(delivery):
    outside = snapshot(SNAPSHOT_AT - timedelta(minutes=30))
    TopGainersLosersSeriesCrud.notify_fastest_movers(
        outside, snapshot(rising=("A",)), "test"
    )
    delivery.assert_called_once()


@pytest.mark.parametrize(
    "age", [timedelta(minutes=15), timedelta(minutes=30), timedelta(seconds=-1)]
)
def test_only_alerts_inside_the_fifteen_minute_window_are_sent(age, clock, delivery):
    clock.now.return_value = SNAPSHOT_AT + age
    TopGainersLosersSeriesCrud.notify_fastest_movers(
        snapshot(SNAPSHOT_AT - timedelta(minutes=30)), snapshot(rising=("A",)), "test"
    )
    delivery.assert_not_called()


def test_expiry_is_checked_before_each_send(clock, delivery):
    clock.now.side_effect = [
        SNAPSHOT_AT + timedelta(minutes=2),
        SNAPSHOT_AT + timedelta(minutes=15),
    ]
    TopGainersLosersSeriesCrud.notify_fastest_movers(
        snapshot(SNAPSHOT_AT - timedelta(minutes=30)),
        snapshot(rising=("A", "B")),
        "test",
    )
    delivery.assert_called_once()


@pytest.mark.parametrize("missing_comparison", ["previous", "current"])
def test_waits_for_valid_hourly_rankings(missing_comparison, delivery):
    previous = snapshot(SNAPSHOT_AT - timedelta(minutes=30))
    current = snapshot(rising=("A",))
    if missing_comparison == "previous":
        previous.comparison_at = None
    else:
        current.comparison_at = None
    TopGainersLosersSeriesCrud.notify_fastest_movers(previous, current, "test")
    delivery.assert_not_called()


def test_missing_ingestion_slot_establishes_a_quiet_baseline(delivery):
    TopGainersLosersSeriesCrud.notify_fastest_movers(
        snapshot(SNAPSHOT_AT - timedelta(hours=1)), snapshot(rising=("A",)), "test"
    )
    delivery.assert_not_called()


@pytest.fixture
def ingestion(test_engine, clock, monkeypatch):
    with Session(test_engine, expire_on_commit=False) as session:
        session.exec(delete(FuturesPriceSampleTable))
        session.exec(delete(TopGainersLosersSeriesTable))
        session.add(
            TopGainersLosersSeriesTable(
                source="kucoin_futures",
                recorded_at=SNAPSHOT_AT - timedelta(minutes=30),
                side="gainer",
                rank=1,
                symbol="AUSDCM",
                price_change_percent=99,
            )
        )
        for minutes, prices in (
            (90, {"AUSDCM": 100, "BUSDCM": 100}),
            (60, {"AUSDCM": 100, "BUSDCM": 100}),
            (30, {"AUSDCM": 110, "BUSDCM": 101}),
        ):
            session.add_all(
                FuturesPriceSampleTable(
                    source="kucoin_futures",
                    recorded_at=SNAPSHOT_AT - timedelta(minutes=minutes),
                    symbol=symbol,
                    last_price=price,
                    price_change_percent=99,
                    turnover_24h=100000,
                )
                for symbol, price in prices.items()
            )
        session.commit()
        settings = SimpleNamespace(fiat="USDC", telegram_signals=True)
        monkeypatch.setattr(
            movers_crud.AutotradeCrud, "get_settings", lambda _self: settings
        )
        contracts = [
            SimpleNamespace(
                symbol=symbol,
                status="Open",
                settle_currency="USDC",
                is_inverse=False,
                last_trade_price=price,
                turnover_of24h=100000,
                price_chg_pct=change,
            )
            for symbol, price, change in (("AUSDCM", 105, 0.99), ("BUSDCM", 120, 0.01))
        ]
        exchange = Mock()
        exchange.futures_market_api.get_all_symbols.return_value = SimpleNamespace(
            data=contracts
        )
        monkeypatch.setattr(movers_crud, "KucoinFutures", Mock(return_value=exchange))
        clock.now.return_value = SNAPSHOT_AT
        yield session, settings
        session.exec(delete(FuturesPriceSampleTable))
        session.exec(delete(TopGainersLosersSeriesTable))
        session.commit()


def test_ingestion_commits_before_notifying_new_one_hour_leader(
    ingestion, delivery, monkeypatch
):
    session, _settings = ingestion
    committed = Mock(wraps=session.commit)
    monkeypatch.setattr(session, "commit", committed)
    observations = []

    def capture_delivery(message):
        observations.append(
            (
                committed.call_count,
                len(session.exec(select(TopGainersLosersSeriesTable)).all()),
                message,
            )
        )
        return True

    delivery.side_effect = capture_delivery
    rows = TopGainersLosersSeriesCrud(session=session).ingest(top=1)
    assert rows[0].symbol == "AUSDCM"  # 24h history stays independent of the 1h alert.
    delivery.assert_called_once()
    commit_count, persisted_count, message = observations[0]
    assert commit_count == 1
    assert persisted_count == 3
    assert "#BUSDCM" in message
    assert "1h price change: +20.00%" in message


def test_telegram_toggle_keeps_ingestion_enabled(ingestion, delivery):
    session, settings = ingestion
    settings.telegram_signals = False
    assert TopGainersLosersSeriesCrud(session=session).ingest(top=1)
    assert len(session.exec(select(FuturesPriceSampleTable)).all()) == 8
    delivery.assert_not_called()


@pytest.mark.parametrize("sent", [True, False])
def test_processed_membership_is_not_replayed_by_a_fresh_crud_instance(
    ingestion, clock, delivery, sent
):
    session, _settings = ingestion
    delivery.return_value = sent
    TopGainersLosersSeriesCrud(session=session).ingest(top=1)
    clock.now.return_value = SNAPSHOT_AT + timedelta(seconds=1)
    TopGainersLosersSeriesCrud(session=session).ingest(top=1)
    delivery.assert_called_once()


def test_first_ingestion_establishes_a_quiet_baseline(ingestion, delivery):
    session, _settings = ingestion
    session.exec(delete(TopGainersLosersSeriesTable))
    session.commit()
    assert TopGainersLosersSeriesCrud(session=session).ingest(top=1)
    delivery.assert_not_called()


def test_intervening_breadth_sample_does_not_consume_an_entry(ingestion, delivery):
    session, _settings = ingestion
    session.add_all(
        FuturesPriceSampleTable(
            source="kucoin_futures",
            recorded_at=SNAPSHOT_AT - timedelta(minutes=15),
            symbol=symbol,
            last_price=price,
            price_change_percent=99,
            turnover_24h=100000,
        )
        for symbol, price in (("AUSDCM", 105), ("BUSDCM", 120))
    )
    session.commit()
    TopGainersLosersSeriesCrud(session=session).ingest(top=1)
    delivery.assert_called_once()
    assert "#BUSDCM" in delivery.call_args.args[0]
