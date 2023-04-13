import asyncio
import atexit
import os
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from streaming.streaming_controller import StreamingController
from account.assets import Assets

if os.getenv("ENV") != "development" or os.getenv("ENV") != "ci":
    scheduler = BackgroundScheduler()
    assets = Assets()
    scheduler.add_job(
        func=assets.store_balance,
        trigger="cron",
        timezone="Europe/London",
        hour=1,
        minute=0,
        id='store_balance'
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
else:
    logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
    logging.basicConfig(
        level=logging.DEBUG,
        filename=None,
        format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

async def main():
    mu = StreamingController()
    await mu.get_klines()
    # await asyncio.gather(
    #     mu.get_klines(),
    #     mu.get_user_data(),
    # )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(error)
        asyncio.run(main())
