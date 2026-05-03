from datetime import datetime, timezone, timedelta

import pytest
from sqlmodel import Session, delete, select

from databases.crud.signals_crud import SignalsCrud
from databases.tables.signals_table import SignalsTable
from tests import conftest


def _make_session() -> Session:
    assert conftest._test_engine is not None
    return Session(conftest._test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_signals():
    with _make_session() as session:
        session.execute(delete(SignalsTable))
        session.commit()
    yield
    with _make_session() as session:
        session.execute(delete(SignalsTable))
        session.commit()


def test_create_signal_persists_columns_and_jsonb():
    session = _make_session()
    crud = SignalsCrud(session)
    row = crud.create(
        algorithm_name="spike_hunter_v3",
        symbol="BTCUSDC",
        generated_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
        direction="LONG",
        autotrade=True,
        current_regime="TRENDING_UP",
        context={"market_regime": "TRENDING_UP", "advancers_ratio": 1.4},
        bot_params={"pair": "BTCUSDC", "fiat_order_size": 20},
        indicators={"bb_high": 1.1, "bb_mid": 1.0, "bb_low": 0.9, "score": 0.83},
    )

    persisted = session.exec(
        select(SignalsTable).where(SignalsTable.id == row.id)
    ).one()
    assert persisted.algorithm_name == "spike_hunter_v3"
    assert persisted.symbol == "BTCUSDC"
    assert persisted.direction == "LONG"
    assert persisted.autotrade is True
    assert persisted.current_regime == "TRENDING_UP"
    assert persisted.context == {"market_regime": "TRENDING_UP", "advancers_ratio": 1.4}
    assert persisted.bot_params["fiat_order_size"] == 20
    assert persisted.indicators["score"] == 0.83


def test_query_filters_by_algorithm_symbol_and_regime():
    session = _make_session()
    crud = SignalsCrud(session)
    base = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    crud.create(
        algorithm_name="spike_hunter_v3",
        symbol="BTCUSDC",
        generated_at=base,
        direction="LONG",
        current_regime="TRENDING_UP",
    )
    crud.create(
        algorithm_name="spike_hunter_v3",
        symbol="ETHUSDC",
        generated_at=base + timedelta(minutes=5),
        direction="LONG",
        current_regime="CHOPPY",
    )
    crud.create(
        algorithm_name="apex_flow",
        symbol="BTCUSDC",
        generated_at=base + timedelta(minutes=10),
        direction="LONG",
        current_regime="TRENDING_UP",
    )

    spike_only = crud.query(algorithm_name="spike_hunter_v3")
    assert {r.symbol for r in spike_only} == {"BTCUSDC", "ETHUSDC"}

    btc_only = crud.query(symbol="BTCUSDC")
    assert {r.algorithm_name for r in btc_only} == {"spike_hunter_v3", "apex_flow"}

    choppy_only = crud.query(current_regime="CHOPPY")
    assert len(choppy_only) == 1
    assert choppy_only[0].symbol == "ETHUSDC"


def test_query_orders_newest_first():
    session = _make_session()
    crud = SignalsCrud(session)
    base = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    for i in range(3):
        crud.create(
            algorithm_name="apex_flow",
            symbol="BTCUSDC",
            generated_at=base + timedelta(minutes=i),
            direction="LONG",
        )

    rows = crud.query(algorithm_name="apex_flow")
    assert len(rows) == 3
    assert rows[0].generated_at > rows[1].generated_at > rows[2].generated_at


def test_post_signal_endpoint(client):
    response = client.post(
        "/signals",
        json={
            "algorithm_name": "spike_hunter_v3",
            "symbol": "BTCUSDC",
            "generated_at": "2026-04-30T12:00:00+00:00",
            "direction": "LONG",
            "autotrade": True,
            "current_regime": "TRENDING_UP",
            "context": {"market_regime": "TRENDING_UP"},
            "bot_params": {"pair": "BTCUSDC"},
            "indicators": {"score": 0.83},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["algorithm_name"] == "spike_hunter_v3"
    assert body["data"]["context"]["market_regime"] == "TRENDING_UP"


def test_get_signals_endpoint_filters(client):
    session = _make_session()
    crud = SignalsCrud(session)
    base = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    crud.create(
        algorithm_name="spike_hunter_v3",
        symbol="BTCUSDC",
        generated_at=base,
        direction="LONG",
        current_regime="TRENDING_UP",
    )
    crud.create(
        algorithm_name="apex_flow",
        symbol="ETHUSDC",
        generated_at=base + timedelta(minutes=5),
        direction="LONG",
        current_regime="CHOPPY",
    )

    response = client.get("/signals?algorithm_name=spike_hunter_v3")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1
    assert payload[0]["algorithm_name"] == "spike_hunter_v3"
