from pathlib import Path
from time import sleep, time
from databases.utils import get_db_session
from grid_ladders.lifecycle import GridLadderLifecycle
from streaming.position_manager import (
    PositionManager,
    BaseStreaming,
)
from pybinbot import configure_logging

HEARTBEAT_PATH = Path("/tmp/binbot_streaming.heartbeat")


def touch_heartbeat() -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(f"{time()}\n", encoding="utf-8")


def main():
    # initialization data
    bs = BaseStreaming()
    configure_logging(force=True)
    total_count = len(bs.active_bot_pairs)
    index = 0
    while True:
        if index == total_count - 1:
            # Refresh active pairs list
            # because we are no longer loading them by demand with restart_streaming
            # we need to check once in a while in case new bots were created
            bs.get_all_active_pairs()
            total_count = len(bs.active_bot_pairs)
            index = 0

        symbol = bs.active_bot_pairs[index]
        sc = PositionManager(bs, symbol)
        sc.process_deal()
        with get_db_session() as session:
            GridLadderLifecycle(bs, session).process_symbol(symbol)
        touch_heartbeat()
        index += 1
        sleep(15)


if __name__ == "__main__":
    main()
