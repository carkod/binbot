import atexit
import threading
import os

from apscheduler.schedulers.background import BackgroundScheduler
from api.app import create_app

# Import Routes
from api.account.assets import Assets
from api.account.routes import account_blueprint
from api.bots.routes import bot_blueprint
from api.charts.routes import charts_blueprint
from api.deals.routes import deal_blueprint
from api.orders.models.order_sockets import OrderUpdates
from api.orders.models.orders import Orders
from api.orders.routes import order_blueprint
from api.tools.jsonresp import jsonResp
from api.user.routes import user_blueprint
from api.research.routes import research_blueprint
from api.threads import market_update_thread
from api.research.correlation import Correlation

app = create_app()

# Cronjob
scheduler = BackgroundScheduler()
assets = Assets()
orders = Orders()
research_data = Correlation()

if os.environ["ENV"] != "development":
    scheduler.add_job(
        func=assets.store_balance, trigger="cron", timezone="Europe/London", hour=00, minute=1
    )
    scheduler.add_job(
        func=market_update_thread, trigger="interval", timezone="Europe/London", hours=2
    )

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))

# Register Blueprints
app.register_blueprint(user_blueprint, url_prefix="/user")
app.register_blueprint(account_blueprint, url_prefix="/account")
app.register_blueprint(bot_blueprint, url_prefix="/bot")
app.register_blueprint(deal_blueprint, url_prefix="/deal")
app.register_blueprint(order_blueprint, url_prefix="/order")
app.register_blueprint(charts_blueprint, url_prefix="/charts")
app.register_blueprint(research_blueprint, url_prefix="/research")


# Index Route
@app.route("/")
def index():
    return jsonResp({"status": "Online"}, 200)


order_updates = OrderUpdates()
# start a worker process to move the received stream_data from the stream_buffer to a print function
worker_thread = threading.Thread(name="order_updates_thread", target=order_updates.run_stream)
worker_thread.start()

# Research market updates
if os.environ["ENV"] != "development":
    market_update_thread()
