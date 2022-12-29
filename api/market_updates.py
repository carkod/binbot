import asyncio
import atexit
import os

from apscheduler.schedulers.background import BackgroundScheduler
from streaming.streaming_controller import StreamingController

from api.account.assets import Assets

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


async def main():
    mu = StreamingController()
    await asyncio.gather(
        mu.get_klines("5m"),
        mu.get_user_data(),
    )


if __name__ == "__main__":
    asyncio.run(main())
