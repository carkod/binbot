import atexit
import os
import threading
import uvicorn

from apscheduler.schedulers.background import BackgroundScheduler
from api.account.assets import Assets
from api.app import create_app
from api.orders.models.order_sockets import OrderUpdates
from api.research.market_updates import MarketUpdates
from api.tools.handle_error import jsonResp

# Routes
from api.account.routes import account_blueprint
from api.bots.routes import bot_blueprint
from api.charts.routes import charts_blueprint
from api.orders.routes import order_blueprint
from api.research.routes import research_blueprint
from api.user.routes import user_blueprint
from api.paper_trading.routes import paper_trading_blueprint
from api.autotrade.routes import autotrade_settings_blueprint
from fastapi import BackgroundTasks, FastAPI


app = create_app()

@app.get("/")
def index():
    return jsonResp({"status": "Online"})


# Register Blueprints
# app.register_blueprint(user_blueprint)
# app.register_blueprint(account_blueprint, url_prefix="/account")
# app.register_blueprint(bot_blueprint)
# app.register_blueprint(order_blueprint, url_prefix="/order")
# app.register_blueprint(charts_blueprint, url_prefix="/charts")
# app.register_blueprint(research_blueprint, url_prefix="/research")
# app.register_blueprint(paper_trading_blueprint)
# app.register_blueprint(autotrade_settings_blueprint, url_prefix="/autotrade-settings")

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

async def run_websockets():
    order_updates = OrderUpdates()
    BackgroundTasks.add_task(order_updates.run_stream())

    # Research market updates
    market_updates = MarketUpdates()
    BackgroundTasks.add_task(market_updates.start_stream())
    yield

if os.getenv("ENV") != "ci":
    @app.on_event("startup")
    async def startup_event():
        OrderUpdates().run_stream()
        MarketUpdates().start_stream()
        return

    # @app.on_event("shutdown")
    # async def shutdown_event():
    #     await global_listener.stop_listening()
    #     return


if __name__ == "__main__":
    uvicorn.run("api.main:app", port=8006)