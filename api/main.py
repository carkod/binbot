import asyncio
import atexit
import os

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Request

from api.app import create_app

asyncio.Event.connection_open = True
app = create_app()

# if os.getenv("ENV") != "development" or os.getenv("ENV") != "ci":
#     scheduler = BackgroundScheduler()
#     assets = Assets()
#     scheduler.add_job(
#         func=assets.store_balance,
#         trigger="cron",
#         timezone="Europe/London",
#         hour=1,
#         minute=0,
#         id='store_balance'
#     )
#     scheduler.start()
#     atexit.register(lambda: scheduler.shutdown(wait=False))
