from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlmodel import Session, delete, select

from charts.controllers import MarketDominationController
from databases.tables.autotrade_table import AutotradeTable
from databases.tables.market_breadth_table import MarketBreadthTable
from pybinbot import ExchangeId
from tests import conftest


def _make_session() -> Session:
    assert conftest._test_engine is not None, (
        "create_test_tables fixture has not initialised the engine yet"
    )
    return Session(conftest._test_engine, expire_on_commit=False)


def _make_controller(
    exchange_id: ExchangeId, session: Session, fiat: str = "USDC"
) -> MarketDominationController:
    controller = MarketDominationController.__new__(MarketDominationController)
    controller.session = session
    controller.exchange = exchange_id
    controller.autotrade_settings = AutotradeTable(fiat=fiat, exchange_id=exchange_id)
    return controller


@pytest.fixture(autouse=True)
def _clean_market_breadth():
    with _make_session() as session:
        session.execute(delete(MarketBreadthTable))
        session.commit()
    yield
    with _make_session() as session:
        session.execute(delete(MarketBreadthTable))
        session.commit()


def test_ingest_adp_data_uses_binance_ticker_payload():
    session = _make_session()
    controller = _make_controller(ExchangeId.BINANCE, session)
    controller.binance_api = SimpleNamespace(  # type: ignore[assignment]
        ticker_24=lambda: [
            {
                "symbol": "BTCUSDC",
                "lastPrice": "100",
                "priceChangePercent": "10",
                "volume": "5",
                "closeTime": 1710000000000,
            },
            {
                "symbol": "ETHUSDC",
                "lastPrice": "200",
                "priceChangePercent": "-5",
                "volume": "2",
                "closeTime": 1710000000000,
            },
            {
                "symbol": "XRPBTC",
                "lastPrice": "1",
                "priceChangePercent": "25",
                "volume": "99",
                "closeTime": 1710000000000,
            },
        ]
    )

    inserted = controller.ingest_adp_data()

    assert inserted is not None
    assert inserted["advancers"] == 1
    assert inserted["decliners"] == 1
    assert inserted["total_volume"] == 7.0
    assert inserted["strength_index"] == pytest.approx(1 / 3)
    assert inserted["adp"] == 0.0
    assert inserted["avg_gain"] == pytest.approx(10.0)
    assert inserted["avg_loss"] == pytest.approx(5.0)
    assert inserted["source"] == ExchangeId.BINANCE.value

    rows = session.exec(select(MarketBreadthTable)).all()
    assert len(rows) == 1
    assert rows[0].advancers == 1
    assert rows[0].decliners == 1
    assert rows[0].source == ExchangeId.BINANCE.value


def test_ingest_adp_data_uses_kucoin_all_tickers_payload():
    session = _make_session()
    controller = _make_controller(ExchangeId.KUCOIN, session)
    controller.kucoin_api = SimpleNamespace(  # type: ignore[assignment]
        spot_api=SimpleNamespace(
            get_all_tickers=lambda: SimpleNamespace(
                common_response=SimpleNamespace(
                    data={
                        "time": 1710000000000,
                        "ticker": [
                            {
                                "symbol": "BTC-USDC",
                                "last": "100",
                                "changeRate": "0.1",
                                "vol": "500",
                            },
                            {
                                "symbol": "ETH-USDC",
                                "last": "200",
                                "changeRate": "-0.05",
                                "vol": "200",
                            },
                            {
                                "symbol": "XRP-BTC",
                                "last": "1",
                                "changeRate": "0.25",
                                "vol": "999",
                            },
                        ],
                    }
                )
            )
        )
    )

    inserted = controller.ingest_adp_data()

    assert inserted is not None
    assert inserted["advancers"] == 1
    assert inserted["decliners"] == 1
    assert inserted["total_volume"] == 700.0
    assert inserted["strength_index"] == pytest.approx(1 / 3)
    assert inserted["adp"] == 0.0
    assert inserted["source"] == ExchangeId.KUCOIN.value


def test_ingest_adp_data_skips_duplicate_timestamp_source():
    session = _make_session()
    controller = _make_controller(ExchangeId.BINANCE, session)

    def payload_factory():
        return [
            {
                "symbol": "BTCUSDC",
                "lastPrice": "100",
                "priceChangePercent": "10",
                "volume": "5",
                "closeTime": 1710000000000,
            }
        ]

    controller.binance_api = SimpleNamespace(ticker_24=payload_factory)  # type: ignore[assignment]

    first = controller.ingest_adp_data()
    second = controller.ingest_adp_data()

    assert first is not None
    assert second is None  # unique constraint on (timestamp, source)
    rows = session.exec(select(MarketBreadthTable)).all()
    assert len(rows) == 1


def test_gainers_losers_uses_coingecko_kucoin_futures_usdt_perpetuals():
    session = _make_session()
    controller = _make_controller(ExchangeId.KUCOIN, session, fiat="USDT")
    controller.coingecko_api = SimpleNamespace(  # type: ignore[assignment]
        get_kucoin_futures_tickers=lambda: [
            {
                "symbol": "ETHUSDTM",
                "base": "ETH",
                "target": "USDT",
                "contract_type": "perpetual",
                "last": 3000.0,
                "h24_percentage_change": 8.0,
                "open_interest_usd": 1000000.0,
                "h24_volume": 2000000.0,
                "funding_rate": 0.01,
                "last_traded": 1710000000,
                "expired_at": None,
            },
            {
                "symbol": "BTCUSDTM",
                "base": "BTC",
                "target": "USDT",
                "contract_type": "perpetual",
                "last": 65000.0,
                "h24_percentage_change": 12.0,
                "open_interest_usd": 5000000.0,
                "h24_volume": 9000000.0,
                "funding_rate": 0.02,
                "last_traded": 1710000000,
                "expired_at": None,
            },
            {
                "symbol": "SOLUSDTM",
                "base": "SOL",
                "target": "USDT",
                "contract_type": "perpetual",
                "last": 150.0,
                "h24_percentage_change": -5.0,
                "open_interest_usd": 700000.0,
                "h24_volume": 600000.0,
                "funding_rate": -0.01,
                "last_traded": 1710000000,
                "expired_at": None,
            },
            {
                "symbol": "XBTUSDM",
                "base": "XBT",
                "target": "USD",
                "contract_type": "perpetual",
                "last": 65000.0,
                "h24_percentage_change": 50.0,
                "open_interest_usd": 100000.0,
                "h24_volume": 100000.0,
                "funding_rate": 0.0,
                "last_traded": 1710000000,
                "expired_at": None,
            },
            {
                "symbol": "ADAUSDT-20240628",
                "base": "ADA",
                "target": "USDT",
                "contract_type": "futures",
                "last": 0.5,
                "h24_percentage_change": 40.0,
                "open_interest_usd": 100000.0,
                "h24_volume": 100000.0,
                "funding_rate": 0.0,
                "last_traded": 1710000000,
                "expired_at": None,
            },
            {
                "symbol": "OLDUSDTM",
                "base": "OLD",
                "target": "USDT",
                "contract_type": "perpetual",
                "last": 1.0,
                "h24_percentage_change": 30.0,
                "open_interest_usd": 100000.0,
                "h24_volume": 100000.0,
                "funding_rate": 0.0,
                "last_traded": 1710000000,
                "expired_at": 1710000000,
            },
        ]
    )

    gainers, losers = controller.gainers_losers()

    assert [item["symbol"] for item in gainers] == ["BTCUSDTM", "ETHUSDTM"]
    assert [item["symbol"] for item in losers] == ["SOLUSDTM"]


def _seed_rows(session: Session, source: str, count: int):
    base = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(count):
        session.add(
            MarketBreadthTable(
                timestamp=base.replace(hour=i),
                source=source,
                advancers=10 + i,
                decliners=5 + i,
                adp=(10 + i - (5 + i)) / (10 + i + 5 + i),
                avg_gain=1.0,
                avg_loss=0.5,
                total_volume=100.0 * (i + 1),
                strength_index=0.4,
            )
        )
    session.commit()


def test_get_adrs_returns_parallel_arrays_newest_first():
    session = _make_session()
    _seed_rows(session, ExchangeId.BINANCE.value, count=5)

    controller = _make_controller(ExchangeId.BINANCE, session)
    result = controller.get_adrs(size=3, window=2)

    # fetch_size = size + window - 1 = 4
    assert result is not None
    assert len(result["timestamp"]) == 4
    # newest first
    assert result["timestamp"][0] > result["timestamp"][-1]
    # all stored fields are present
    for key in (
        "timestamp",
        "advancers",
        "decliners",
        "adp",
        "adp_ma",
        "avg_gain",
        "avg_loss",
        "total_volume",
        "strength_index",
    ):
        assert key in result
        assert len(result[key]) == 4
    # adp_ma is computed; first row in chronological order has just itself in the window
    assert result["adp_ma"][-1] == pytest.approx(result["adp"][-1])


def test_get_adrs_filters_by_exchange():
    session = _make_session()
    _seed_rows(session, ExchangeId.BINANCE.value, count=3)
    _seed_rows(session, ExchangeId.KUCOIN.value, count=3)

    controller = _make_controller(ExchangeId.BINANCE, session)
    result = controller.get_adrs(size=10, window=1, exchange=ExchangeId.KUCOIN)

    # only kucoin rows should be returned
    assert result is not None
    assert len(result["timestamp"]) == 3


def test_get_adrs_returns_none_when_empty():
    session = _make_session()
    controller = _make_controller(ExchangeId.BINANCE, session)
    assert controller.get_adrs() is None
