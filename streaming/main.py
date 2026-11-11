import sys
from pathlib import Path
from time import monotonic, sleep, time

HEARTBEAT_PATH = Path("/tmp/binbot_streaming.heartbeat")
SWEEP_INTERVAL_SECONDS = 15


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


def main():
    # Configure before loading the worker's dependency graph. Keeping this in
    # main avoids changing import behaviour in API/cronjobs or test processes.
    sys.set_lazy_imports_filter(defer_dependency_import)
    sys.set_lazy_imports("all")

    from api.databases.utils import get_db_session
    from api.grid_ladders.lifecycle import GridLadderLifecycle
    from streaming.position_manager import BaseStreaming, PositionManager
    from pybinbot import configure_logging

    bs = BaseStreaming()
    configure_logging(force=True)
    while True:
        sweep_started_at = monotonic()
        for symbol in tuple(bs.active_bot_pairs):
            manager = PositionManager(bs, symbol)
            manager.process_deal()
            with get_db_session() as session:
                GridLadderLifecycle(bs, session).process_symbol(symbol)
            touch_heartbeat()

        bs.get_all_active_pairs()
        sleep(
            max(
                0.0,
                SWEEP_INTERVAL_SECONDS - (monotonic() - sweep_started_at),
            )
        )


if __name__ == "__main__":
    main()
