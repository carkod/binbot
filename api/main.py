import asyncio
import atexit
import os

import uvicorn
from app import create_app
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Request
from starlette.responses import PlainTextResponse
from streaming.streaming_controller import StreamingController
from app import create_app

asyncio.Event.connection_open = True

app = create_app()

# if __name__ == "__main__":
#     uvicorn.run("main:app", port=5000, log_level="info", workers=3)

