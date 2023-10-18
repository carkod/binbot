import atexit
import os
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from streaming.streaming_controller import StreamingController
from account.assets import Assets
from websocket import (
    WebSocketException,
    WebSocketConnectionClosedException,
)


logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if os.getenv("ENV") != "ci":

    scheduler = BackgroundScheduler()
    assets = Assets()
    timezone = "Europe/London"

    scheduler.add_job(
        func=assets.store_balance,
        trigger="cron",
        timezone=timezone,
        hour=1,
        minute=1,
        id="store_balance",
    )
    
    scheduler.add_job(
        func=assets.disable_isolated_accounts,
        trigger="cron",
        timezone=timezone,
        hour=2,
        minute=1,
        id="disable_isolated_accounts",
    )

    scheduler.add_job(
        func=assets.clean_balance_assets,
        trigger="cron",
        timezone=timezone,
        hour=3,
        minute=1,
        id="clean_balance_assets",
    )
    scheduler.start()

try:
    mu = StreamingController()
    mu.get_klines()

except WebSocketException as e:
    if isinstance(e, WebSocketConnectionClosedException):
        logging.error("Lost websocket connection")
        mu = StreamingController()
        mu.get_klines()
    else:
        logging.error(f"Websocket exception: {e}")
    
    atexit.register(lambda: scheduler.shutdown(wait=False))

except Exception as error:
    logging.error(f"Streaming controller error: {error}")
    mu = StreamingController()
    mu.get_klines()

    atexit.register(lambda: scheduler.shutdown(wait=False))
