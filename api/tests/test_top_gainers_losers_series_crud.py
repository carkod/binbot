from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, delete, select

from api.databases.crud.top_gainers_losers_series_crud import TopGainersLosersSeriesCrud
from api.databases.tables.autotrade_table import AutotradeTable
from api.databases.tables.futures_price_sample_table import FuturesPriceSampleTable
from api.databases.tables.top_gainers_losers_series_table import (
    TopGainersLosersSeriesTable,
)

_engine = None


def _make_session() -> Session:
    assert _engine is not None
    return Session(_engine, expire_on_commit=False)


def _contract(
    symbol: str,
    price_change_percent: float,
    *,
    settle_currency: str = "USDC",
    status: str = "Open",
    is_inverse: bool = False,
    last_trade_price: float = 1.0,
    turnover_of24h: float = 1_000.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        symbol=symbol,
        price_chg_pct=price_change_percent / 100,
        settle_currency=settle_currency,
        status=status,
        is_inverse=is_inverse,
        last_trade_price=last_trade_price,
        turnover_of24h=turnover_of24h,
    )


def _ingest_with_fake_contracts(
    session: Session, contracts: list[SimpleNamespace], top: int = 10
) -> list[TopGainersLosersSeriesTable]:
    with patch(
        "api.databases.crud.top_gainers_losers_series_crud.KucoinFutures"
    ) as kucoin_futures_cls:
        kucoin_futures_cls.return_value = MagicMock(
            futures_market_api=MagicMock(
                get_all_symbols=MagicMock(return_value=SimpleNamespace(data=contracts))
            )
        )
        rows = TopGainersLosersSeriesCrud(session=session).ingest(top=top)
        kucoin_futures_cls.return_value.futures_market_api.get_all_symbols.assert_called_once()
        return rows


@pytest.fixture(autouse=True)
def _clean_top_gainers_losers_series(test_engine):
    global _engine
    _engine = test_engine
    with _make_session() as session:
        session.execute(delete(TopGainersLosersSeriesTable))
        session.execute(delete(FuturesPriceSampleTable))
        session.commit()
    yield
    with _make_session() as session:
        session.execute(delete(TopGainersLosersSeriesTable))
        session.execute(delete(FuturesPriceSampleTable))
        session.commit()


def test_ingest_ranks_gainers_and_losers_by_percent_change():
    session = _make_session()
    contracts = [
        _contract("AUSDCM", 25.0),
        _contract("BUSDCM", -12.0),
        _contract("CUSDCM", 5.0),
        _contract("DUSDCM", -3.0),
        _contract("EUSDCM", 1.0),
        _contract("FBTCM", 99.0, settle_currency="BTC"),
    ]

    rows = _ingest_with_fake_contracts(session, contracts, top=2)

    assert len(rows) == 4
    gainers = sorted((r for r in rows if r.side == "gainer"), key=lambda r: r.rank)
    losers = sorted((r for r in rows if r.side == "loser"), key=lambda r: r.rank)

    assert [(g.rank, g.symbol, g.price_change_percent) for g in gainers] == [
        (1, "AUSDCM", 25.0),
        (2, "CUSDCM", 5.0),
    ]
    assert [
        (loser.rank, loser.symbol, loser.price_change_percent) for loser in losers
    ] == [
        (1, "BUSDCM", -12.0),
        (2, "DUSDCM", -3.0),
    ]
    assert {row.source for row in rows} == {"kucoin_futures"}
    assert [(g.last_price, g.turnover_24h) for g in gainers] == [
        (1.0, 1_000.0),
        (1.0, 1_000.0),
    ]


def test_ingest_excludes_closed_or_inactive_futures_contracts():
    """
    KuCoin's all-symbols response includes closed contracts and contracts
    without recent trading, which must not occupy a top rank.
    """
    session = _make_session()
    contracts = [
        _contract("AUSDCM", 25.0),
        _contract("DEADUSDCM", 999.0, status="Closed"),
        _contract("CUSDCM", 5.0),
        _contract("GHOSTUSDCM", -999.0, turnover_of24h=0.0),
        _contract("DUSDCM", -3.0),
    ]

    rows = _ingest_with_fake_contracts(session, contracts, top=2)

    symbols = {r.symbol for r in rows}
    assert "DEADUSDCM" not in symbols
    assert "GHOSTUSDCM" not in symbols
    assert symbols == {"AUSDCM", "CUSDCM", "DUSDCM"}


def test_ingest_persists_rows():
    session = _make_session()
    contracts = [_contract("AUSDCM", 10.0), _contract("BUSDCM", -10.0)]

    _ingest_with_fake_contracts(session, contracts, top=1)

    persisted = session.exec(select(TopGainersLosersSeriesTable)).all()
    assert len(persisted) == 2
    assert {p.symbol for p in persisted} == {"AUSDCM", "BUSDCM"}
    price_samples = session.exec(select(FuturesPriceSampleTable)).all()
    assert {sample.symbol for sample in price_samples} == {"AUSDCM", "BUSDCM"}


def test_futures_price_samples_keep_seven_days_of_full_market_history():
    session = _make_session()
    now = datetime.now(timezone.utc)
    session.add_all(
        FuturesPriceSampleTable(
            source="kucoin_futures",
            recorded_at=now - timedelta(hours=hours_ago),
            symbol=symbol,
            last_price=1.0,
            price_change_percent=2.0,
            turnover_24h=100.0,
        )
        for hours_ago, symbol in ((167, "RECENTUSDCM"), (169, "EXPIREDUSDCM"))
    )
    session.commit()

    TopGainersLosersSeriesCrud.record_futures_prices(session, [], now)
    session.commit()

    assert {
        sample.symbol for sample in session.exec(select(FuturesPriceSampleTable))
    } == {"RECENTUSDCM"}


def test_fastest_movers_ranks_hourly_price_moves_outside_top_gainers():
    session = _make_session()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    samples: list[FuturesPriceSampleTable] = []
    for hours_ago, prices in (
        (3, {"TOPUSDCM": 95.0, "FASTUSDCM": 80.0, "DOWNUSDCM": 100.0}),
        (1, {"TOPUSDCM": 100.0, "FASTUSDCM": 100.0, "DOWNUSDCM": 100.0}),
        (0, {"TOPUSDCM": 101.0, "FASTUSDCM": 110.0, "DOWNUSDCM": 90.0}),
    ):
        samples.extend(
            FuturesPriceSampleTable(
                source="kucoin_futures",
                recorded_at=now - timedelta(hours=hours_ago),
                symbol=symbol,
                last_price=price,
                price_change_percent=99.0 if symbol == "TOPUSDCM" else 5.0,
                turnover_24h=10_000.0,
            )
            for symbol, price in prices.items()
        )
    session.add_all(samples)
    session.commit()

    result = TopGainersLosersSeriesCrud(session=session).query_fastest_movers(limit=2)

    assert [item["symbol"] for item in result["gainers"]] == [
        "FASTUSDCM",
        "TOPUSDCM",
    ]
    assert result["gainers"][0]["price_change_1h_percent"] == pytest.approx(10.0)
    assert result["gainers"][0]["price_change_3h_percent"] == pytest.approx(37.5)
    assert result["losers"][0]["symbol"] == "DOWNUSDCM"
    assert result["losers"][0]["price_change_1h_percent"] == pytest.approx(-10.0)


def test_fastest_movers_waits_for_an_hourly_comparison():
    session = _make_session()
    session.add(
        FuturesPriceSampleTable(
            source="kucoin_futures",
            recorded_at=datetime.now(timezone.utc),
            symbol="ONLYUSDCM",
            last_price=10.0,
            price_change_percent=15.0,
            turnover_24h=10_000.0,
        )
    )
    session.commit()

    result = TopGainersLosersSeriesCrud(session=session).query_fastest_movers()

    assert result["comparison_at"] is None
    assert result["gainers"] == []
    assert result["losers"] == []


def test_fastest_movers_prefers_snapshot_closest_to_one_hour():
    session = _make_session()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    session.add_all(
        FuturesPriceSampleTable(
            source="kucoin_futures",
            recorded_at=now - timedelta(minutes=minutes_ago),
            symbol="FASTUSDCM",
            last_price=price,
            price_change_percent=25.0,
            turnover_24h=10_000.0,
        )
        for minutes_ago, price in ((60, 100.0), (55, 105.0), (0, 110.0))
    )
    session.commit()

    result = TopGainersLosersSeriesCrud(session=session).query_fastest_movers()

    assert result["gainers"][0]["price_change_1h_percent"] == pytest.approx(10.0)


def test_get_fastest_movers_endpoint(client):
    session = _make_session()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    session.add_all(
        FuturesPriceSampleTable(
            source="kucoin_futures",
            recorded_at=now - timedelta(hours=hours_ago),
            symbol="FASTUSDCM",
            last_price=price,
            price_change_percent=25.0,
            turnover_24h=10_000.0,
        )
        for hours_ago, price in ((1, 100.0), (0, 105.0))
    )
    session.commit()

    response = client.get("/charts/fastest_movers?limit=1")

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["source"] == "kucoin_futures"
    assert body["gainers"][0]["symbol"] == "FASTUSDCM"
    assert body["gainers"][0]["price_change_1h_percent"] == pytest.approx(5.0)
    assert body["losers"] == []


def test_ingest_uses_fiat_from_autotrade_settings():
    session = _make_session()
    settings = session.get(AutotradeTable, "autotrade_settings")
    assert settings is not None
    original_fiat = settings.fiat

    try:
        settings.fiat = "BTC"
        session.add(settings)
        session.commit()

        rows = _ingest_with_fake_contracts(
            session,
            [
                _contract("AUSDCM", 25.0),
                _contract("XBTUSDM", 10.0, settle_currency="BTC"),
            ],
            top=1,
        )

        assert {row.symbol for row in rows} == {"XBTUSDM"}
    finally:
        settings = session.get(AutotradeTable, "autotrade_settings")
        assert settings is not None
        settings.fiat = original_fiat
        session.add(settings)
        session.commit()


def test_query_series_groups_by_snapshot_newest_first():
    session = _make_session()
    older = datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)
    newer = older + timedelta(days=1)

    session.add_all(
        [
            TopGainersLosersSeriesTable(
                recorded_at=older,
                side="gainer",
                rank=1,
                symbol="AUSDC",
                price_change_percent=10.0,
            ),
            TopGainersLosersSeriesTable(
                recorded_at=older,
                side="loser",
                rank=1,
                symbol="BUSDC",
                price_change_percent=-10.0,
            ),
            TopGainersLosersSeriesTable(
                recorded_at=newer,
                side="gainer",
                rank=1,
                symbol="CUSDC",
                price_change_percent=20.0,
            ),
            TopGainersLosersSeriesTable(
                recorded_at=newer,
                side="loser",
                rank=1,
                symbol="DUSDC",
                price_change_percent=-20.0,
            ),
        ]
    )
    session.commit()

    result = TopGainersLosersSeriesCrud(session=session).query_series(limit=7)

    assert len(result) == 2
    assert result[0]["source"] == "kucoin_futures"
    # SQLite (test DB) drops tzinfo on round-trip, unlike Postgres.
    assert result[0]["recorded_at"] == newer.replace(tzinfo=None)
    assert result[0]["top_gainers"] == [
        {
            "symbol": "CUSDC",
            "price_change_percent": 20.0,
            "last_price": None,
            "turnover_24h": None,
        }
    ]
    assert result[0]["top_losers"] == [
        {
            "symbol": "DUSDC",
            "price_change_percent": -20.0,
            "last_price": None,
            "turnover_24h": None,
        }
    ]
    assert result[1]["recorded_at"] == older.replace(tzinfo=None)


def test_query_series_returns_empty_list_when_no_data():
    session = _make_session()
    assert TopGainersLosersSeriesCrud(session=session).query_series() == []


def test_delete_entries_older_than_one_year_removes_only_stale_rows():
    session = _make_session()
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            TopGainersLosersSeriesTable(
                recorded_at=now - timedelta(days=366),
                side="gainer",
                rank=1,
                symbol="STALEUSDC",
                price_change_percent=10.0,
            ),
            TopGainersLosersSeriesTable(
                recorded_at=now - timedelta(days=364),
                side="gainer",
                rank=1,
                symbol="RECENTUSDC",
                price_change_percent=10.0,
            ),
        ]
    )
    session.commit()

    deleted_count = TopGainersLosersSeriesCrud().delete_entries_older_than_one_year()

    assert deleted_count == 1
    rows = session.exec(select(TopGainersLosersSeriesTable)).all()
    assert {row.symbol for row in rows} == {"RECENTUSDC"}


def test_get_gainers_losers_series_endpoint(client):
    session = _make_session()
    recorded_at = datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)
    session.add_all(
        [
            TopGainersLosersSeriesTable(
                recorded_at=recorded_at,
                side="gainer",
                rank=1,
                symbol="AUSDC",
                price_change_percent=10.0,
            ),
            TopGainersLosersSeriesTable(
                recorded_at=recorded_at,
                side="loser",
                rank=1,
                symbol="BUSDC",
                price_change_percent=-10.0,
            ),
        ]
    )
    session.commit()

    response = client.get("/charts/gainers-losers-series")

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["source"] == "kucoin_futures"
    assert body[0]["top_gainers"] == [
        {
            "symbol": "AUSDC",
            "price_change_percent": 10.0,
            "last_price": None,
            "turnover_24h": None,
        }
    ]
    assert body[0]["top_losers"] == [
        {
            "symbol": "BUSDC",
            "price_change_percent": -10.0,
            "last_price": None,
            "turnover_24h": None,
        }
    ]


def test_get_gainers_losers_series_defaults_to_seven_days_of_hourly_snapshots(client):
    session = _make_session()
    oldest = datetime(2026, 8, 10, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(169):
        recorded_at = oldest + timedelta(hours=index)
        rows.extend(
            [
                TopGainersLosersSeriesTable(
                    recorded_at=recorded_at,
                    side="gainer",
                    rank=1,
                    symbol=f"G{index}USDC",
                    price_change_percent=10.0,
                ),
                TopGainersLosersSeriesTable(
                    recorded_at=recorded_at,
                    side="loser",
                    rank=1,
                    symbol=f"L{index}USDC",
                    price_change_percent=-10.0,
                ),
            ]
        )
    session.add_all(rows)
    session.commit()

    response = client.get("/charts/gainers-losers-series")

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 168
    assert body[0]["top_gainers"][0]["symbol"] == "G168USDC"
    assert body[-1]["top_gainers"][0]["symbol"] == "G1USDC"


def test_get_gainers_losers_series_endpoint_404_when_empty(client):
    response = client.get("/charts/gainers-losers-series")
    assert response.status_code == 404
