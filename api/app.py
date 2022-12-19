import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

from api.account.routes import router as account_blueprint
from api.autotrade.routes import autotrade_settings_blueprint
from api.bots.routes import bot_blueprint
from api.charts.routes import charts_blueprint
from api.orders.routes import order_blueprint
from api.paper_trading.routes import paper_trading_blueprint
from api.research.routes import research_blueprint
from api.user.routes import user_blueprint
from api.streaming.streaming_controller import StreamingController


def start_streaming(app):
    """
    Replacement for old restart_sockets and terminate_websockets

    If for whatever reason (errors, exceptions, failed bots) streaming stopped,
    we want to resume streaming to avoid asset loss
    """
    try:
        mu = StreamingController(app=app)
        loop = asyncio.get_event_loop()
        loop.create_task(mu.get_klines("5m"), name="klines")
        loop.create_task(mu.get_user_data(), name="user_data")
    except Exception as error:
        print(f"Streaming error: {error}")
        start_streaming()


def create_app():
    app = FastAPI()

    # Enable CORS for all routes
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Database
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    app.db = mongo[os.getenv("MONGO_APP_DATABASE")]

    # Routes
    @app.get("/", description="Index endpoint for testing that the API app works")
    def index():
        return {"status": "Online"}

    app.include_router(user_blueprint)
    app.include_router(account_blueprint, prefix="/account")
    app.include_router(bot_blueprint)
    app.include_router(paper_trading_blueprint)
    app.include_router(order_blueprint, prefix="/order")
    app.include_router(charts_blueprint, prefix="/charts")
    app.include_router(research_blueprint, prefix="/research")
    app.include_router(autotrade_settings_blueprint, prefix="/autotrade-settings")

    # Streaming
    # can only start when endpoints are ready
    start_streaming(app)

    return app
