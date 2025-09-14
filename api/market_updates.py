import asyncio
from streaming.streaming_controller import (
    StreamingController,
    BaseStreaming,
)
from tools.logging_config import configure_logging

# initialization data
bs = BaseStreaming()
total_count = len(bs.active_bot_pairs)


async def process_klines():
    index = 0
    while True:
        if index >= total_count:
            index = 0

        symbol = bs.active_bot_pairs[index]
        sc = StreamingController(bs, symbol)
        sc.process_klines()
        await asyncio.sleep(30)


async def dynamic_trailing():
    index = 0
    while True:
        if index >= total_count:
            index = 0

        symbol = bs.active_bot_pairs[index]
        sc = StreamingController(bs, symbol)
        sc.dynamic_trailling()
        await asyncio.sleep(30)


async def main():
    configure_logging(force=True)
    updates_task = asyncio.create_task(process_klines())
    trailing_task = asyncio.create_task(dynamic_trailing())
    await asyncio.gather(updates_task, trailing_task)


if __name__ == "__main__":
    asyncio.run(main())
