import asyncio
from app import create_app

asyncio.Event.connection_open = True

app = create_app()
