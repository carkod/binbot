import asyncio
import os
import logging
import time

from streaming.streaming_controller import StreamingController
from websocket import WebSocketConnectionClosedException


logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

async def streaming_main():
    mu = StreamingController()
    await asyncio.gather(
        mu.get_klines(),
        # mu.get_user_data()
    )

try:
    asyncio.run(streaming_main())
except Exception as error:
    logging.error(f"Streaming controller error: {error}")
    asyncio.run(streaming_main())
