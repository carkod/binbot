import atexit
import os
import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from api.account.assets import Assets
from api.app import create_app
from api.orders.models.order_sockets import OrderUpdates
from api.research.controller import Controller
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

app = create_app()


@app.route("/")
def index():
    return jsonResp({"status": "Online"})


# Register Blueprints
app.register_blueprint(user_blueprint)
app.register_blueprint(account_blueprint, url_prefix="/account")
app.register_blueprint(bot_blueprint)
app.register_blueprint(order_blueprint, url_prefix="/order")
app.register_blueprint(charts_blueprint, url_prefix="/charts")
app.register_blueprint(research_blueprint, url_prefix="/research")
app.register_blueprint(paper_trading_blueprint)
app.register_blueprint(autotrade_settings_blueprint, url_prefix="/autotrade-settings")

if os.getenv("ENV") != "development" or os.getenv("ENV") != "ci":
    scheduler = BackgroundScheduler()
    assets = Assets()
    scheduler.add_job(
        func=assets.store_balance,
        trigger="cron",
        timezone="Europe/London",
        hour=1,
        minute=0
    )
    controller = Controller()
    scheduler.add_job(
        func=controller.store_profitable_signals,
        trigger="cron",
        timezone="Europe/London",
        hour=2,
        minute=0,
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))

if os.getenv("ENV") != "ci":
    async def main():
        order_updates = OrderUpdates()
        market_updates = MarketUpdates()
        await asyncio.gather(
            order_updates.run_stream(),
            market_updates.start_stream()
        )

    if __name__ == "__main__":
        asyncio.run(main())
