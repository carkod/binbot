import asyncio
import logging
import random
import signal
import sys
from pathlib import Path
from threading import Event
from time import monotonic, time

HEARTBEAT_PATH = Path("/tmp/binbot_streaming.heartbeat")
SWEEP_INTERVAL_SECONDS = 15
log = logging.getLogger(__name__)


def defer_dependency_import(
    importing_module: str | None,
    _imported_module: str,
    _fromlist: tuple[str, ...] | None,
) -> bool:
    """Defer unused SDK exports while keeping application registration eager."""
    return importing_module is not None and (
        importing_module == "pybinbot"
        or importing_module.startswith("pybinbot.")
        or importing_module == "kucoin_universal_sdk"
        or importing_module.startswith("kucoin_universal_sdk.")
    )


def touch_heartbeat() -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(f"{time()}\n", encoding="utf-8")


def run_positions(stop: Event) -> None:
    """Keep blocking position work sequential and off the collector event loop."""
    from api.databases.utils import get_db_session
    from api.grid_ladders.lifecycle import GridLadderLifecycle
    from streaming.position_manager import BaseStreaming, PositionManager

    bs = BaseStreaming()
    while not stop.is_set():
        sweep_started_at = monotonic()
        for symbol in tuple(bs.active_bot_pairs):
            if stop.is_set():
                return
            manager = PositionManager(bs, symbol)
            manager.process_deal()
            with get_db_session() as session:
                GridLadderLifecycle(bs, session).process_symbol(symbol)
            touch_heartbeat()

        if stop.is_set():
            return
        bs.get_all_active_pairs()
        touch_heartbeat()
        stop.wait(max(0.0, SWEEP_INTERVAL_SECONDS - (monotonic() - sweep_started_at)))


async def supervise_cvd(stop: asyncio.Event) -> None:
    """Restart collection failures without interrupting position management."""
    from streaming.cvd import run

    failures = 0
    while not stop.is_set():
        started = monotonic()
        try:
            await run(stop)
            if stop.is_set():
                return
            raise RuntimeError("CVD collection exited unexpectedly")
        except Exception:
            failures = 1 if monotonic() - started >= 60 else min(failures + 1, 6)
            delay = min(60, 2**failures) + random.uniform(0, 1)
            log.exception("CVD collection failed; restarting in %.1fs", delay)
            try:
                await asyncio.wait_for(stop.wait(), delay)
            except TimeoutError:
                pass


async def run_worker() -> None:
    stop = asyncio.Event()
    positions_stop = Event()
    loop = asyncio.get_running_loop()

    def shutdown() -> None:
        positions_stop.set()
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(asyncio.to_thread(run_positions, positions_stop))
            group.create_task(supervise_cvd(stop))
    finally:
        shutdown()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


def main() -> None:
    # Configure before loading the worker's dependency graph. Keeping this in
    # main avoids changing import behaviour in API/cronjobs or test processes.
    sys.set_lazy_imports_filter(defer_dependency_import)
    sys.set_lazy_imports("all")

    from pybinbot import configure_logging

    configure_logging(force=True)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
