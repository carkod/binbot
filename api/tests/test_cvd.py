"""Execution, coverage and persistence contracts for the central collector."""

import os
from datetime import datetime, timezone
from functools import partial
from importlib import import_module
from time import perf_counter
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session

from api.charts.routes import charts_blueprint
from api.databases.crud.cvd_crud import query_cvd_aggregate, query_cvd_symbol
from api.databases.tables.cvd_table import SOURCE, CvdBucketTable, CvdMinuteTable
from api.databases.utils import get_session
from streaming.cvd.contracts import discover_contracts
from streaming.cvd.flow import Flow, handle_message
from streaming.cvd.storage import acquire_owner, persist, restore
from streaming.shared.kucoin_futures import stream_executions

# UTC aligned exchange minute, far above seconds/milliseconds timestamp ranges.
START = 1_790_000_040


def flow_at_start(contracts=None):
    flow = Flow(contracts or {"SOLUSDTM": 0.1}, START * 1_000_000_000)
    flow.acknowledged = {symbol: START - 1 for symbol in flow.contracts}
    flow.tick(START)
    return flow


def execution(symbol="SOLUSDTM", trade_id="1", side="buy", second=1):
    return {
        "symbol": symbol,
        "tradeId": trade_id,
        "side": side,
        "price": "71.738",
        "size": 4,
        "ts": (START + second) * 1_000_000_000,
    }


def test_execution_uses_taker_side_contract_multiplier_and_symbol_qualified_ids():
    flow = flow_at_start({"SOLUSDTM": 0.1, "OTHERUSDTM": 0.01})
    assert flow.trade(execution(), START + 2)
    assert not flow.trade(execution(), START + 2)
    assert flow.trade(execution(symbol="OTHERUSDTM"), START + 2)
    assert flow.trade(execution(trade_id="2", side="sell"), START + 2)
    assert flow.minutes[START].symbols["SOLUSDTM"].buy == pytest.approx(28.6952)
    assert flow.minutes[START].symbols["SOLUSDTM"].sell == pytest.approx(28.6952)
    assert flow.minutes[START].symbols["OTHERUSDTM"].buy == pytest.approx(2.86952)


@pytest.mark.parametrize(
    "overrides",
    [
        {"ts": 1_790_000_040},
        {"ts": 1_790_000_040_000},
        {"ts": (START + 9) * 10**9},
        {"ts": "NaN"},
        {"size": -1},
        {"size": 0.5},
        {"price": "nan"},
        {"price": "inf"},
        {"side": "unknown"},
        {"tradeId": None},
        {"symbol": "unknown"},
    ],
)
def test_untrusted_or_future_executions_are_rejected(overrides):
    flow = flow_at_start()
    assert not flow.trade(execution() | overrides, START + 2)
    assert flow.rejected == 1
    assert flow.minutes[START].symbols["SOLUSDTM"].buy == 0


def test_minute_boundary_late_arrival_and_finalization():
    flow = flow_at_start()
    flow.tick(START + 60)
    assert flow.trade(execution(second=60), START + 60)
    assert flow.trade(execution(trade_id="late", second=59), START + 121)
    assert flow.minutes[START + 60].symbols["SOLUSDTM"].buy > 0
    assert flow.minutes[START].symbols["SOLUSDTM"].buy > 0
    assert not flow.trade(execution(trade_id="too-late", second=1), START + 122)
    _, snapshots = flow.snapshot(START + 179)
    assert not snapshots[0]["finalized"]
    assert flow.snapshot(START + 180)[1][0]["finalized"]
    flow.prune(START + 181)
    assert START not in flow.seen


def test_quiet_acknowledged_market_differs_from_disconnected_market():
    flow = flow_at_start({"A": 0.1, "B": 0.01})
    flow.disconnect(["B"], START + 20)
    minute = flow.snapshot(START + 40)[1][0]
    assert minute["buy"] == minute["sell"] == 0
    assert minute["expected_symbols"] == 2
    assert minute["covered_symbols"] == 1
    flow.acknowledged["B"] = START + 30
    for second in range(10, 81, 10):
        flow.tick(START + second)
    assert not flow.minutes[START].symbols["B"].covered
    assert flow.minutes[START + 60].symbols["B"].covered


@pytest.mark.parametrize("last_second,resumed_second", [(10, 40), (50, 135)])
@pytest.mark.parametrize("disconnected", [False, True])
def test_scheduler_stall_marks_gaps_and_recovers_future_coverage(
    last_second, resumed_second, disconnected
):
    flow = flow_at_start({"A": 0.1, "B": 0.01})
    if disconnected:
        flow.disconnect(["B"], START + 5)
    for second in range(10, last_second + 1, 10):
        flow.tick(START + second)
    flow.tick(START + resumed_second)
    affected_minutes = list(flow.minutes)
    for minute in affected_minutes:
        assert not flow.minutes[minute].symbols["A"].covered
        assert not flow.minutes[minute].symbols["B"].covered
    assert "A" in flow.acknowledged
    assert ("B" not in flow.acknowledged) == disconnected
    next_minute = resumed_second // 60 * 60 + 60
    for second in range(resumed_second + 10, next_minute + 11, 10):
        flow.tick(START + second)
    for minute in affected_minutes:
        assert not flow.minutes[minute].symbols["A"].covered
    recovered = flow.minutes[START + next_minute]
    assert recovered.symbols["A"].covered
    assert recovered.symbols["B"].covered == (not disconnected)
    snapshots = {row["minute"]: row for row in flow.snapshot(START + next_minute)[1]}
    expected_covered = 1 if disconnected else 2
    assert snapshots[START + next_minute]["covered_symbols"] == expected_covered


def test_acknowledgement_and_invalid_payload_coverage():
    flow = flow_at_start()
    flow.disconnect(["SOLUSDTM"], START)
    pending = {"sub": ("SOLUSDTM", 0.0)}
    with patch("streaming.cvd.flow.time.time", return_value=START + 1):
        handle_message(flow, {"type": "ack", "id": "sub"}, pending, ["SOLUSDTM"])
    assert not pending
    assert flow.acknowledged["SOLUSDTM"] == START + 1
    with pytest.raises(ValueError):
        handle_message(flow, {"type": "error"}, pending, ["SOLUSDTM"])
    for second in range(10, 71, 10):
        flow.tick(START + second)
    with patch("streaming.cvd.flow.time.time", return_value=START + 71):
        handle_message(
            flow,
            {
                "type": "message",
                "subject": "match",
                "topic": "/contractMarket/execution:SOLUSDTM",
                "data": execution(second=70) | {"price": "nan"},
            },
            pending,
            ["SOLUSDTM"],
        )
    assert not flow.minutes[START + 60].symbols["SOLUSDTM"].covered


def test_metadata_change_is_effective_next_minute_and_freezes_multiplier():
    flow = flow_at_start()
    flow.contracts = {"SOLUSDTM": 0.2, "NEW": 0.01}
    for second in range(10, 71, 10):
        flow.tick(START + second)
    assert "NEW" not in flow.minutes[START].symbols
    assert "NEW" in flow.minutes[START + 60].symbols
    assert flow.trade(execution(), START + 71)
    assert flow.trade(execution(trade_id="new", second=60), START + 71)
    assert flow.minutes[START + 60].symbols["SOLUSDTM"].buy == pytest.approx(
        2 * flow.minutes[START].symbols["SOLUSDTM"].buy
    )
    assert flow.minutes[START].universe != flow.minutes[START + 60].universe


def test_active_registered_linear_usdt_universe_includes_quiet_contracts():
    contract = {
        "symbol": "A",
        "status": "Open",
        "settleCurrency": "USDT",
        "isInverse": False,
        "multiplier": ".001",
    }
    assert discover_contracts(
        [
            contract,
            contract | {"symbol": "B"},
            contract | {"symbol": "C", "isInverse": True},
            contract | {"symbol": "D", "status": "Closed"},
            contract | {"symbol": "E", "settleCurrency": "USDC"},
        ],
        {"A", "C", "D", "E"},
    ) == {"A": 0.001}


@pytest.fixture
def cvd_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    for model in (CvdBucketTable, CvdMinuteTable):
        getattr(model, "__table__").create(engine)
    yield engine
    engine.dispose()


def test_restart_fences_saved_future_minutes_per_symbol_and_allows_new_late_trades(
    cvd_engine,
):
    flow = flow_at_start({"SOLUSDTM": 0.1, "OTHERUSDTM": 0.1})
    assert flow.trade(execution(second=59), START + 58)
    assert flow.trade(execution(trade_id="future", second=60), START + 58)
    assert flow.trade(execution(symbol="OTHERUSDTM", second=57), START + 58)
    with Session(cvd_engine) as session:
        for model, rows in zip(
            (CvdBucketTable, CvdMinuteTable), flow.snapshot(START + 58)
        ):
            session.add_all(model(**row) for row in rows)
        session.commit()
    restarted = Flow(flow.contracts, (START + 59) * 10**9)
    with cvd_engine.connect() as connection:
        restore(connection, restarted)
    assert not restarted.trade(execution(second=59), START + 60)
    assert not restarted.trade(execution(trade_id="future", second=60), START + 60)
    assert not restarted.trade(execution(trade_id="uncertain", second=60), START + 60)
    assert restarted.trade(execution(symbol="OTHERUSDTM", second=59), START + 60)
    assert restarted.trade(execution(trade_id="new", second=64), START + 64)
    assert restarted.trade(execution(trade_id="late", second=62), START + 65)
    assert not restarted.trade(execution(trade_id="late", second=62), START + 66)
    assert restarted.minutes[START + 60].symbols["SOLUSDTM"].buy == pytest.approx(
        3 * 28.6952
    )
    restarted.acknowledged = {symbol: START + 66 for symbol in flow.contracts}
    for second in range(70, 131, 10):
        restarted.tick(START + second)
    for minute in (START, START + 60):
        assert not restarted.minutes[minute].symbols["SOLUSDTM"].covered
    assert restarted.minutes[START + 120].symbols["SOLUSDTM"].covered


def test_migration_replays_on_new_and_partially_migrated_schemas():
    migration = import_module("api.alembic.versions.c8d71b9e204f_add_cvd_buckets")
    for partially_migrated in (False, True):
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            if partially_migrated:
                connection.execute(
                    text(
                        "CREATE TABLE cvd_bucket (source VARCHAR(32), symbol VARCHAR(64), minute BIGINT, PRIMARY KEY (source, symbol, minute))"
                    )
                )
                connection.execute(
                    text("INSERT INTO cvd_bucket VALUES ('kucoin_futures', 'A', 60)")
                )
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()
                assert {
                    c["name"] for c in inspect(connection).get_columns("cvd_bucket")
                } >= {"multiplier", "buy", "sell", "covered", "last_trade_ns"}
                if partially_migrated:
                    assert connection.execute(
                        text("SELECT buy, covered FROM cvd_bucket")
                    ).one() == (0, 0)
                migration.downgrade()
                migration.downgrade()
                assert not inspect(connection).has_table("cvd_minute")
        engine.dispose()


def test_aggregate_arithmetic_gaps_fixed_window_and_universe_history(cvd_engine):
    start = START // 900 * 900
    now = start + 3 * 900 + 30
    with Session(cvd_engine) as session:
        for minute in range(start, start + 900, 60):
            session.add(
                CvdMinuteTable(
                    source=SOURCE,
                    minute=minute,
                    buy=100,
                    sell=20,
                    expected_symbols=2,
                    covered_symbols=2,
                    universe="first",
                    finalized=True,
                    updated_at=datetime.fromtimestamp(now, timezone.utc),
                )
            )
        session.add(
            CvdMinuteTable(
                source=SOURCE,
                minute=start + 1800,
                buy=30,
                sell=10,
                expected_symbols=3,
                covered_symbols=1,
                universe="new",
                finalized=False,
                updated_at=datetime.fromtimestamp(now, timezone.utc),
            )
        )
        session.commit()
        result = query_cvd_aggregate(session, 4, now)
    first, outage, changed, current = result["data"]
    assert first["buy"] == 1500
    assert first["sell"] == 300
    assert first["cvd"] == 1200
    assert first["complete"]
    assert outage["gap"] and outage["cvd"] is None
    assert changed["cvd"] == 1220 and changed["universe_changed"]
    assert current["current"] and current["gap"]
    assert result["reset_at"].timestamp() == start
    assert result["partial"] and not result["stale"]


def test_api_bounds_empty_and_staleness(cvd_engine):
    app = FastAPI()
    app.include_router(charts_blueprint, prefix="/charts")

    def session():
        with Session(cvd_engine) as db:
            yield db

    app.dependency_overrides[get_session] = session
    with patch("api.charts.routes.time", return_value=START) as clock:
        client = TestClient(app)
        for suffix in ("limit=0", "limit=673", "limit=bad"):
            assert client.get("/charts/cvd-aggregate?" + suffix).status_code == 422
        assert clock.call_count == 0
        response = client.get("/charts/cvd-aggregate?limit=1")
        assert response.status_code == 200
        assert response.json()["stale"] and response.json()["data"] == []
        with Session(cvd_engine) as db:
            db.add(
                CvdMinuteTable(
                    source=SOURCE,
                    minute=START,
                    buy=42,
                    sell=2,
                    expected_symbols=717,
                    covered_symbols=700,
                    universe="one",
                    finalized=False,
                    updated_at=datetime.fromtimestamp(START - 91, timezone.utc),
                )
            )
            db.commit()
        response = client.get("/charts/cvd-aggregate?limit=1")
        assert response.status_code == 200
        point = response.json()["data"][0]
        assert point["cvd"] == 40
        assert point["expected_symbols"] == 717
        assert point["covered_symbols"] == 700
        assert point["gap"] and response.json()["stale"]


def test_representative_execution_load_stays_bounded():
    flow = flow_at_start({f"S{i}": 0.001 for i in range(780)})
    started = perf_counter()
    for i in range(50_000):
        assert flow.trade(execution(symbol=f"S{i % 780}", trade_id=str(i)), START + 2)
    assert flow.trades == 50_000
    assert len(flow.snapshot(START + 2)[0]) == 780
    # A generous budget detects accidental per-execution I/O or quadratic dedup.
    assert perf_counter() - started < 10
    flow.prune(START + 181)
    assert not flow.seen


@pytest.mark.skipif(
    __import__("os").getenv("CVD_TEST_POSTGRES_URL") is None,
    reason="isolated PostgreSQL URL required",
)
@pytest.mark.parametrize("saved_second", [1, 4])
def test_postgres_owner_snapshot_retry_and_restart(saved_second):

    engine = create_engine(os.environ["CVD_TEST_POSTGRES_URL"])
    for model in (CvdBucketTable, CvdMinuteTable):
        getattr(model, "__table__").create(engine, checkfirst=True)
    with engine.connect() as owner, engine.connect() as other:
        acquire_owner(owner)
        with pytest.raises(RuntimeError, match="Another"):
            acquire_owner(other)
        other.rollback()
        flow = flow_at_start()
        assert flow.trade(execution(second=saved_second), START + 1)
        snapshot = flow.snapshot(START + 1)
        persist(owner, snapshot, START + 1)
        persist(owner, snapshot, START + 1)
        restarted = Flow(flow.contracts, (START + 2) * 10**9)
        restore(owner, restarted)
        assert restarted.minutes[START].symbols["SOLUSDTM"].buy == pytest.approx(
            28.6952
        )
        assert not restarted.minutes[START].symbols["SOLUSDTM"].covered
        assert not restarted.trade(execution(second=saved_second), START + 3)
        assert restarted.trade(execution(trade_id="after", second=5), START + 5)
        persist(owner, restarted.snapshot(START + 5), START + 5)
        assert owner.execute(
            text("SELECT buy FROM cvd_minute WHERE minute=:minute"), {"minute": START}
        ).scalar_one() == pytest.approx(57.3904)
        owner.rollback()
        owner.invalidate()
        acquire_owner(other)
        other.invalidate()
    engine.dispose()


def test_first_execution_in_new_minute_does_not_wait_for_checkpoint_tick():
    flow = flow_at_start()
    assert flow.trade(execution(second=60), START + 60)
    assert flow.minutes[START + 60].symbols["SOLUSDTM"].buy == pytest.approx(28.6952)


def test_plausible_exchange_clock_skew_can_cross_minute_boundary():
    flow = flow_at_start()
    assert flow.trade(execution(second=60), START + 58)
    assert flow.minutes[START + 60].symbols["SOLUSDTM"].buy == pytest.approx(28.6952)


@pytest.mark.asyncio
async def test_websocket_ack_ping_and_reconnect_gap(monkeypatch):
    import asyncio
    import json
    import time
    from websockets.asyncio.server import serve

    flow = Flow({"SOLUSDTM": 0.1}, time.time_ns())
    flow.tick(time.time())
    subscribed = asyncio.Event()
    received_ping = asyncio.Event()
    connections = []

    async def exchange(ws):
        connections.append(ws)
        await ws.send(json.dumps({"type": "welcome"}))
        async for raw in ws:
            message = json.loads(raw)
            if message["type"] == "subscribe":
                assert message["topic"] == "/contractMarket/execution:SOLUSDTM"
                assert message["response"]
                await ws.send(json.dumps({"type": "ack", "id": message["id"]}))
                await ws.send(
                    json.dumps(
                        {
                            "type": "message",
                            "subject": "match",
                            "topic": "/contractMarket/execution:SOLUSDTM",
                            "data": execution() | {"ts": time.time_ns()},
                        }
                    )
                )
                subscribed.set()
            elif message["type"] == "ping":
                received_ping.set()
                await ws.send(json.dumps({"type": "pong", "id": message["id"]}))

    async with serve(exchange, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        monkeypatch.setattr(
            "streaming.shared.kucoin_futures.public_request",
            lambda *args: {
                "token": "test",
                "instanceServers": [
                    {
                        "endpoint": f"ws://127.0.0.1:{port}",
                        "pingInterval": 100,
                        "pingTimeout": 1000,
                    }
                ],
            },
        )
        stop = asyncio.Event()
        task = asyncio.create_task(
            stream_executions(
                ["SOLUSDTM"], stop, partial(handle_message, flow), flow.disconnect
            )
        )
        try:
            await asyncio.wait_for(subscribed.wait(), 2)
            await asyncio.wait_for(received_ping.wait(), 2)
            assert "SOLUSDTM" in flow.acknowledged
            assert flow.trades == 1
            assert sum(
                b.buy for m in flow.minutes.values() for b in m.symbols.values()
            ) == pytest.approx(28.6952)
            await connections[0].close()
            for _ in range(100):
                if "SOLUSDTM" not in flow.acknowledged:
                    break
                await asyncio.sleep(0.01)
            assert "SOLUSDTM" not in flow.acknowledged
            assert not flow.snapshot(time.time())[1][0]["covered_symbols"]
        finally:
            stop.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["ack", "pong"])
async def test_missing_ack_or_pong_invalidates_subscription(monkeypatch, missing):
    import asyncio
    import json
    import time
    from websockets.asyncio.server import serve

    flow = Flow({"SOLUSDTM": 0.1}, time.time_ns())
    flow.tick(time.time())
    closed = asyncio.Event()

    async def exchange(ws):
        await ws.send(json.dumps({"type": "welcome"}))
        try:
            async for raw in ws:
                message = json.loads(raw)
                if message["type"] == "subscribe" and missing != "ack":
                    await ws.send(json.dumps({"type": "ack", "id": message["id"]}))
                if message["type"] == "ping" and missing != "pong":
                    await ws.send(json.dumps({"type": "pong", "id": message["id"]}))
        finally:
            closed.set()

    async with serve(exchange, "127.0.0.1", 0) as server:
        monkeypatch.setattr("streaming.shared.kucoin_futures.ACK_TIMEOUT", 0.1)
        monkeypatch.setattr(
            "streaming.shared.kucoin_futures.public_request",
            lambda *args: {
                "token": "test",
                "instanceServers": [
                    {
                        "endpoint": f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}",
                        "pingInterval": 100,
                        "pingTimeout": 100,
                    }
                ],
            },
        )
        stop = asyncio.Event()
        task = asyncio.create_task(
            stream_executions(
                ["SOLUSDTM"], stop, partial(handle_message, flow), flow.disconnect
            )
        )
        try:
            await asyncio.wait_for(closed.wait(), 3)
            await asyncio.sleep(0.01)
            assert not flow.acknowledged
            assert not flow.snapshot(time.time())[1][0]["covered_symbols"]
        finally:
            stop.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def save_symbol_minute(
    session,
    minute,
    *,
    symbol="SOLUSDTM",
    source=SOURCE,
    buy=0,
    sell=0,
    covered=True,
    finalized=True,
    multiplier=0.1,
    updated_at=None,
    universe="all",
    market_covered=717,
):
    session.add(
        CvdBucketTable(
            source=source,
            symbol=symbol,
            minute=minute,
            buy=buy,
            sell=sell,
            covered=covered,
            multiplier=multiplier,
        )
    )
    if session.get(CvdMinuteTable, (source, minute)) is None:
        session.add(
            CvdMinuteTable(
                source=source,
                minute=minute,
                buy=99999,
                sell=999,
                expected_symbols=717,
                covered_symbols=market_covered,
                universe=universe,
                finalized=finalized,
                updated_at=datetime.fromtimestamp(
                    updated_at if updated_at is not None else minute, timezone.utc
                ),
            )
        )
    session.commit()


def test_symbol_cvd_uses_own_notional_coverage_and_multiplier_history(cvd_engine):
    now = START + 5 * 60 + 20
    with Session(cvd_engine) as session:
        save_symbol_minute(session, START - 60, buy=999)
        save_symbol_minute(session, START, buy=100, sell=20)
        # A quiet covered market stays complete despite other markets' outages
        # or changes to the registered universe.
        save_symbol_minute(session, START + 60, universe="changed", market_covered=1)
        save_symbol_minute(session, START + 180, buy=7, sell=10, covered=False)
        save_symbol_minute(
            session, START + 240, buy=20, multiplier=0.2, finalized=False
        )
        save_symbol_minute(
            session,
            START + 300,
            buy=1,
            sell=2,
            multiplier=0.2,
            finalized=False,
            updated_at=now,
        )
        save_symbol_minute(session, START, symbol="OTHERUSDTM", buy=999)
        save_symbol_minute(session, START, source="other_exchange", buy=999)
        result = query_cvd_symbol(session, "SOLUSDTM", 6, now)
    first, quiet, missing, disconnected, mutable, current = result["data"]
    assert first["buy"] == 100 and first["sell"] == 20 and first["cvd"] == 80
    assert first["complete"] and first["expected_symbols"] == 1
    assert quiet["cvd"] == 80 and quiet["buy"] == quiet["sell"] == 0
    assert quiet["complete"] and not quiet["universe_changed"]
    assert missing["gap"] and missing["cvd"] is None
    assert missing["buy"] is None and missing["observed_minutes"] == 0
    assert disconnected["cvd"] == 77 and disconnected["covered_symbols"] == 0
    assert disconnected["gap"]
    assert mutable["cvd"] == 97 and mutable["universe_changed"] and mutable["gap"]
    assert current["cvd"] == 96 and current["current"] and current["gap"]
    assert not current["universe_changed"]
    assert result["reset_at"].timestamp() == START
    assert result["source"] == SOURCE and result["symbol"] == "SOLUSDTM"
    assert result["partial"] and not result["stale"]


def test_symbol_freshness_does_not_follow_other_markets(cvd_engine):
    with Session(cvd_engine) as session:
        save_symbol_minute(session, START, buy=12, updated_at=START)
        save_symbol_minute(
            session, START + 180, symbol="OTHERUSDTM", updated_at=START + 180
        )
        result = query_cvd_symbol(session, "SOLUSDTM", 4, START + 180)
        assert result["stale"] and result["updated_at"].timestamp() == START
        assert result["data"][0]["cvd"] == 12
        assert result["data"][-1]["cvd"] is None
        # A delisted symbol still has readable history, until retention removes it.
        empty = query_cvd_symbol(session, "UNKNOWN", 4, START + 180)
        assert empty["data"] == [] and empty["stale"] and empty["updated_at"] is None
        # A selected window with only finalized quiet observations is complete.
        quiet = query_cvd_symbol(session, "SOLUSDTM", 1, START)
        assert not quiet["partial"]


def test_symbol_api_validates_bounds_normalizes_symbol_and_returns_saved_data(
    cvd_engine,
):
    app = FastAPI()
    app.include_router(charts_blueprint, prefix="/charts")

    def session():
        with Session(cvd_engine) as db:
            yield db

    app.dependency_overrides[get_session] = session
    with Session(cvd_engine) as db:
        save_symbol_minute(db, START, buy=123.456789, sell=23.0, finalized=False)
    client = TestClient(app)
    with patch("api.charts.routes.time", return_value=START) as clock:
        for suffix in (
            "",
            "symbol=",
            "symbol=SOL/USDTM",
            "symbol=" + "A" * 65,
            "symbol=SOLUSDTM&limit=0",
            "symbol=SOLUSDTM&limit=10081",
            "symbol=SOLUSDTM&limit=bad",
        ):
            assert client.get("/charts/cvd-symbol?" + suffix).status_code == 422
        assert clock.call_count == 0
        response = client.get("/charts/cvd-symbol?symbol=solusdtm&limit=1")
        assert response.status_code == 200
        result = response.json()
        assert result["symbol"] == "SOLUSDTM" and not result["stale"]
        assert result["data"][0]["cvd"] == pytest.approx(100.456789)
        assert result["data"][0]["current"] and result["data"][0]["gap"]
        assert (
            len(client.get("/charts/cvd-symbol?symbol=SOLUSDTM").json()["data"]) == 15
        )
        assert (
            len(
                client.get("/charts/cvd-symbol?symbol=SOLUSDTM&limit=10080").json()[
                    "data"
                ]
            )
            == 10080
        )
        assert client.get("/charts/cvd-symbol?symbol=UNKNOWN").json()["data"] == []
