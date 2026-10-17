from pathlib import Path
from time import monotonic, sleep, time
from api.databases.utils import get_db_session
from api.grid_ladders.lifecycle import GridLadderLifecycle
from streaming.position_manager import (
    PositionManager,
    BaseStreaming,
)
from pybinbot import configure_logging

HEARTBEAT_PATH = Path("/tmp/binbot_streaming.heartbeat")
SWEEP_INTERVAL_SECONDS = 15


def touch_heartbeat() -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(f"{time()}\n", encoding="utf-8")


def main():
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
