from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, delete, select

from api.databases.crud.top_gainers_losers_series_crud import TopGainersLosersSeriesCrud
from api.databases.tables.top_gainers_losers_series_table import (
    TopGainersLosersSeriesTable,
)

_engine = None


def _make_session() -> Session:
    assert _engine is not None
    return Session(_engine, expire_on_commit=False)


def _ticker(
    symbol: str,
    price_change_percent: float,
    *,
    bid_price: float = 1.0,
    ask_price: float = 1.0,
) -> dict:
    return {
        "symbol": symbol,
        "priceChangePercent": str(price_change_percent),
        "bidPrice": str(bid_price),
        "askPrice": str(ask_price),
    }


def _ingest_with_fake_ticker(
    session: Session, ticker_rows: list[dict], top: int = 10
) -> list[TopGainersLosersSeriesTable]:
    with patch(
        "api.databases.crud.top_gainers_losers_series_crud.BinanceApi"
    ) as binance_api_cls:
        binance_api_cls.return_value = MagicMock(ticker_24=lambda: ticker_rows)
        return TopGainersLosersSeriesCrud(session=session).ingest(top=top)


@pytest.fixture(autouse=True)
def _clean_top_gainers_losers_series(test_engine):
    global _engine
    _engine = test_engine
    with _make_session() as session:
        session.execute(delete(TopGainersLosersSeriesTable))
        session.commit()
    yield
    with _make_session() as session:
        session.execute(delete(TopGainersLosersSeriesTable))
        session.commit()


def test_ingest_ranks_gainers_and_losers_by_percent_change():
    session = _make_session()
    ticker_rows = [
        _ticker("AUSDC", 25.0),
        _ticker("BUSDC", -12.0),
        _ticker("CUSDC", 5.0),
        _ticker("DUSDC", -3.0),
        _ticker("EUSDC", 1.0),
        _ticker("FBTC", 99.0),  # different quote asset, must be excluded
    ]

    rows = _ingest_with_fake_ticker(session, ticker_rows, top=2)

    assert len(rows) == 4
    gainers = sorted((r for r in rows if r.side == "gainer"), key=lambda r: r.rank)
    losers = sorted((r for r in rows if r.side == "loser"), key=lambda r: r.rank)

    assert [(g.rank, g.symbol, g.price_change_percent) for g in gainers] == [
        (1, "AUSDC", 25.0),
        (2, "CUSDC", 5.0),
    ]
    assert [
        (loser.rank, loser.symbol, loser.price_change_percent) for loser in losers
    ] == [
        (1, "BUSDC", -12.0),
        (2, "DUSDC", -3.0),
    ]


def test_ingest_excludes_delisted_symbols_with_no_active_market():
    """
    Delisted/halted symbols keep serving Binance's last real 24h ticker
    window forever (no new trade ever rolls it forward), frozen with a
    zero bid/ask and often an extreme priceChangePercent that would
    otherwise permanently occupy a top rank.
    """
    session = _make_session()
    ticker_rows = [
        _ticker("AUSDC", 25.0),
        _ticker("DEADUSDC", 999.0, bid_price=0.0, ask_price=0.0),
        _ticker("CUSDC", 5.0),
        _ticker("GHOSTUSDC", -999.0, bid_price=0.0, ask_price=0.0),
        _ticker("DUSDC", -3.0),
    ]

    rows = _ingest_with_fake_ticker(session, ticker_rows, top=2)

    symbols = {r.symbol for r in rows}
    assert "DEADUSDC" not in symbols
    assert "GHOSTUSDC" not in symbols
    assert symbols == {"AUSDC", "CUSDC", "DUSDC"}


def test_ingest_persists_rows():
    session = _make_session()
    ticker_rows = [_ticker("AUSDC", 10.0), _ticker("BUSDC", -10.0)]

    _ingest_with_fake_ticker(session, ticker_rows, top=1)

    persisted = session.exec(select(TopGainersLosersSeriesTable)).all()
    assert len(persisted) == 2
    assert {p.symbol for p in persisted} == {"AUSDC", "BUSDC"}


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
    # SQLite (test DB) drops tzinfo on round-trip, unlike Postgres.
    assert result[0]["recorded_at"] == newer.replace(tzinfo=None)
    assert result[0]["top_gainers"] == [
        {"symbol": "CUSDC", "price_change_percent": 20.0}
    ]
    assert result[0]["top_losers"] == [
        {"symbol": "DUSDC", "price_change_percent": -20.0}
    ]
    assert result[1]["recorded_at"] == older.replace(tzinfo=None)


def test_query_series_returns_empty_list_when_no_data():
    session = _make_session()
    assert TopGainersLosersSeriesCrud(session=session).query_series() == []


def test_delete_entries_older_than_90_days_removes_only_stale_rows():
    session = _make_session()
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            TopGainersLosersSeriesTable(
                recorded_at=now - timedelta(days=91),
                side="gainer",
                rank=1,
                symbol="STALEUSDC",
                price_change_percent=10.0,
            ),
            TopGainersLosersSeriesTable(
                recorded_at=now - timedelta(days=89),
                side="gainer",
                rank=1,
                symbol="RECENTUSDC",
                price_change_percent=10.0,
            ),
        ]
    )
    session.commit()

    deleted_count = TopGainersLosersSeriesCrud().delete_entries_older_than_90_days()

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
    assert body[0]["top_gainers"] == [{"symbol": "AUSDC", "price_change_percent": 10.0}]
    assert body[0]["top_losers"] == [{"symbol": "BUSDC", "price_change_percent": -10.0}]


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
