import os
from fastapi import FastAPI
from flask_cors import CORS
from pymongo import MongoClient
from api.research.market_updates import MarketUpdates
from api.orders.models.order_sockets import OrderUpdates
import asyncio
from api.streaming.klines import KlinesStreaming
from binance import AsyncClient, BinanceSocketManager


async def streaming_klines(app):
    mu = MarketUpdates(app=app)
    await mu.start_stream()
    return {"status": "Started streaming klines"}

async def streaming_orders(app):
    mu = OrderUpdates(app=app)
    await mu.run_stream()
    return {"status": "Started streaming orders"}



def create_app():
    print("Starting app...")
    app = FastAPI()

    # Schema
    # db = MongoEngine(app)
    # Enable CORS for all routes
    # CORS(app, expose_headers="Authorization")
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    app.db = mongo[os.getenv("MONGO_APP_DATABASE")]

    @app.get("/")
    def index():
        return {"status": "Online"}


    mu = KlinesStreaming(app=app)
    loop = asyncio.get_event_loop()
    loop.create_task(mu.get_klines("5m"), name="klines")
    loop.create_task(mu.get_user_data(), name="user_data")

    return app
