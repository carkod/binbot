import os
from fastapi import FastAPI
from flask_cors import CORS
from pymongo import MongoClient
from api.research.market_updates import MarketUpdates
import asyncio
from starlette.concurrency import run_in_threadpool



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
    async def index():
        mu = MarketUpdates(app=app)
        await mu.start_stream()
        return {"status": "Online"}

    
    return app




