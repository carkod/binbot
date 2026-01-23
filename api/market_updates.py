from time import sleep
from streaming.position_manager import (
    PositionManager,
    BaseStreaming,
)
from pybinbot import configure_logging


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
        index += 1
        sleep(15)


if __name__ == "__main__":
    main()
