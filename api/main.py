import atexit
import os
import threading

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

app = create_app()


@app.route("/")
def index():
    return jsonResp({"status": "Online"})


# Register Blueprints
app.register_blueprint(user_blueprint, url_prefix="/user")
app.register_blueprint(account_blueprint, url_prefix="/account")
app.register_blueprint(bot_blueprint)
app.register_blueprint(order_blueprint, url_prefix="/order")
app.register_blueprint(charts_blueprint, url_prefix="/charts")
app.register_blueprint(research_blueprint, url_prefix="/research")


if os.getenv("ENV") != "development" or os.getenv("ENV") != "ci":
    scheduler = BackgroundScheduler()
    assets = Assets()
    scheduler.add_job(
        func=assets.store_balance_snapshot, trigger="cron", timezone="Europe/London", hour=00, minute=1

    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))

if os.getenv("ENV") != "ci":
    order_updates = OrderUpdates()
    # start a worker process to move the received stream_data from the stream_buffer to a print function
    worker_thread = threading.Thread(name="order_updates_thread", target=order_updates.run_stream)
    worker_thread.start()

    # Research market updates
    market_updates = MarketUpdates()
    market_updates_thread = threading.Thread(name="market_updates_thread", target=market_updates.start_stream)
    market_updates_thread.start()
