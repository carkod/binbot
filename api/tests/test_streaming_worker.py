import asyncio
import signal
from contextlib import asynccontextmanager
from threading import Event, get_ident
from unittest.mock import Mock

import pytest

from streaming import cvd, main


@pytest.mark.asyncio
async def test_collector_runs_during_blocking_position_work_and_both_stop(monkeypatch):
    positions_started = Event()
    positions_finished = Event()
    signals = {}
    thread_ids = {}
    checkpoints = []
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        loop, "add_signal_handler", lambda sig, cb: signals.update({sig: cb})
    )
    removed = Mock()
    monkeypatch.setattr(loop, "remove_signal_handler", removed)

    def positions(stop):
        thread_ids["positions"] = get_ident()
        positions_started.set()
        assert stop.wait(2), "Worker shutdown did not reach position management"
        positions_finished.set()

    async def collect(stop):
        thread_ids["collector"] = get_ident()
        assert await asyncio.to_thread(positions_started.wait, 1)
        checkpoints.append("collecting while positions wait")
        signals[signal.SIGTERM]()
        assert stop.is_set()
        await asyncio.sleep(0)
        checkpoints.append("final partial checkpoint")

    monkeypatch.setattr(main, "run_positions", positions)
    monkeypatch.setattr(cvd, "run", collect)
    await asyncio.wait_for(main.run_worker(), 3)

    assert positions_finished.is_set()
    assert thread_ids["collector"] == get_ident()
    assert thread_ids["positions"] != thread_ids["collector"]
    assert checkpoints == [
        "collecting while positions wait",
        "final partial checkpoint",
    ]
    assert set(signals) == {signal.SIGTERM, signal.SIGINT}
    assert removed.call_count == 2


@pytest.mark.asyncio
async def test_collector_failures_retry_with_backoff_without_stopping_positions(
    monkeypatch,
):
    stop = asyncio.Event()
    attempts: list[int] = []
    delays = []

    async def collect(shared_stop):
        assert shared_stop is stop
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise RuntimeError("Owner connection lost")
        shared_stop.set()

    async def retry_wait(awaitable, timeout):
        delays.append(timeout)
        awaitable.close()
        await asyncio.sleep(0)
        raise TimeoutError

    monkeypatch.setattr(cvd, "run", collect)
    monkeypatch.setattr(main.random, "uniform", lambda *_: 0.25)
    monkeypatch.setattr(main.asyncio, "wait_for", retry_wait)
    await main.supervise_cvd(stop)

    assert attempts == [1, 2, 3]
    assert delays == [2.25, 4.25]


@pytest.mark.asyncio
async def test_shutdown_interrupts_collector_restart_backoff(monkeypatch):
    stop = asyncio.Event()
    attempts: list[int] = []

    async def collect(shared_stop):
        attempts.append(1)
        asyncio.get_running_loop().call_soon(shared_stop.set)
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(cvd, "run", collect)
    await asyncio.wait_for(main.supervise_cvd(stop), 1)
    assert attempts == [1]


@pytest.mark.asyncio
async def test_position_failure_stops_worker_and_cancels_collection(monkeypatch):
    collecting = Event()
    collector_stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "add_signal_handler", Mock())
    monkeypatch.setattr(loop, "remove_signal_handler", Mock())

    def positions(stop):
        assert collecting.wait(1)
        raise RuntimeError("Position sweep failed")

    async def collect(stop):
        collecting.set()
        try:
            await stop.wait()
        finally:
            collector_stopped.set()

    monkeypatch.setattr(main, "run_positions", positions)
    monkeypatch.setattr(cvd, "run", collect)
    with pytest.raises(ExceptionGroup, match="unhandled errors") as caught:
        await asyncio.wait_for(main.run_worker(), 2)
    assert str(caught.value.exceptions[0]) == "Position sweep failed"
    assert collector_stopped.is_set()


def test_quiet_position_sweeps_refresh_health_and_shutdown_interrupts_sleep(
    monkeypatch,
):
    from streaming import position_manager

    stop = Event()
    base = Mock(active_bot_pairs=[])
    base.get_all_active_pairs.side_effect = stop.set
    monkeypatch.setattr(position_manager, "BaseStreaming", Mock(return_value=base))
    heartbeat = Mock()
    monkeypatch.setattr(main, "touch_heartbeat", heartbeat)

    main.run_positions(stop)

    base.get_all_active_pairs.assert_called_once()
    heartbeat.assert_called_once()


@pytest.mark.asyncio
async def test_embedded_collector_uses_worker_shutdown_and_flushes_final_checkpoint(
    monkeypatch,
):
    stop = asyncio.Event()
    connection = Mock(invalidated=False)
    persisted = []
    loop = asyncio.get_running_loop()
    signal_handler = Mock()
    monkeypatch.setattr(loop, "add_signal_handler", signal_handler)

    @asynccontextmanager
    async def owner():
        yield connection

    def persist(owner_connection, snapshot, now):
        assert owner_connection is connection
        persisted.append(snapshot)
        loop.call_soon_threadsafe(stop.set)

    monkeypatch.setattr(cvd, "owner_connection", owner)
    monkeypatch.setattr(cvd, "load_contracts", lambda: {})
    monkeypatch.setattr(cvd, "restore", Mock())
    monkeypatch.setattr(cvd, "persist", persist)

    await asyncio.wait_for(cvd.run(stop), 2)

    assert len(persisted) == 2  # Regular flush, then graceful final checkpoint.
    assert persisted[0][1][0]["covered_symbols"] == 0
    assert persisted[1][1][0]["finalized"] is False
    signal_handler.assert_not_called()


@pytest.mark.asyncio
async def test_database_ownership_does_not_block_worker_event_loop(monkeypatch):
    connecting = Event()
    release_connection = Event()
    connection = Mock()
    acquired = []

    def connect():
        connecting.set()
        assert release_connection.wait(2)
        return connection

    def acquire(owner):
        assert owner is connection
        acquired.append(get_ident())

    async def own():
        async with cvd.owner_connection() as owner:
            assert owner is connection

    monkeypatch.setattr(cvd.engine, "connect", connect)
    monkeypatch.setattr(cvd, "acquire_owner", acquire)
    task = asyncio.create_task(own())
    try:
        assert await asyncio.to_thread(connecting.wait, 1)
        # The loop can still handle shutdown and heartbeat callbacks during DB I/O.
        await asyncio.sleep(0)
        assert task.done() is False
    finally:
        release_connection.set()
    await asyncio.wait_for(task, 2)
    assert acquired[0] != get_ident()
    connection.invalidate.assert_called_once()
    connection.close.assert_called_once()
