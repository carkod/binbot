import asyncio
from streaming.streaming_controller import (
    StreamingController,
    BaseStreaming,
)
from tools.logging_config import configure_logging

# initialization data
bs = BaseStreaming()
total_count = len(bs.active_bot_pairs)
configure_logging(force=True)


async def process_klines():
    index = 0
    while True:
        if index >= total_count:
            # Refresh active pairs list
            # because we are no longer loading them by demand with restart_streaming
            # we need to check once in a while in case new bots were created
            bs.get_all_active_pairs()
            index = 0

        symbol = bs.active_bot_pairs[index]
        sc = StreamingController(bs, symbol)
        sc.process_klines()
        index += 1
        await asyncio.sleep(10)


async def dynamic_trailing():
    index = 0
    while True:
        if index >= total_count:
            bs.get_all_active_pairs()
            index = 0

        symbol = bs.active_bot_pairs[index]
        sc = StreamingController(bs, symbol)
        sc.dynamic_trailling()
        index += 1
        await asyncio.sleep(10)


async def main():
    updates_task = asyncio.create_task(process_klines())
    trailing_task = asyncio.create_task(dynamic_trailing())
    await asyncio.gather(updates_task, trailing_task)


if __name__ == "__main__":
    asyncio.run(main())
