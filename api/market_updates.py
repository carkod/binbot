import atexit
import os
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from streaming.streaming_controller import StreamingController
from account.assets import Assets
from websocket import WebSocketConnectionClosedException


logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

try:

    mu = StreamingController()
    mu.get_klines()

except WebSocketConnectionClosedException as e:
    logging.error("Lost websocket connection")
    mu = StreamingController()
    mu.get_klines()

except Exception as error:
    logging.error(f"Streaming controller error: {error}")
    mu = StreamingController()
    mu.get_klines()
