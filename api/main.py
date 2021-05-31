import atexit
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from api.app import create_app

# Import Routes
from api.account.models import Assets
from api.account.routes import account_blueprint
from api.bots.routes import bot_blueprint
from api.charts.routes import charts_blueprint
from api.deals.routes import deal_blueprint
from api.orders.models.order_sockets import OrderUpdates
from api.charts.klines_sockets import KlineSockets
from api.orders.models.orders import Orders
from api.orders.routes import order_blueprint
from api.tools.jsonresp import jsonResp
from api.user.routes import user_blueprint
from api.research.routes import research_blueprint
from api.research.market_updates import MarketUpdates

app = create_app()

# Cronjob
scheduler = BackgroundScheduler()
assets = Assets(app)
orders = Orders()

scheduler.add_job(
    func=assets.store_balance, trigger="cron", timezone="Europe/London", hour=0, minute=1
)
scheduler.add_job(
    func=orders.poll_historical_orders,
    trigger="cron",
    timezone="Europe/London",
    hour=1,
    minute=1,
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


order_updates = OrderUpdates(app)
# start a worker process to move the received stream_data from the stream_buffer to a print function
worker_thread = threading.Thread(target=order_updates.run_stream)
worker_thread.start()

kline_updates = KlineSockets()
# start a worker process to move the received stream_data from the stream_buffer to a print function
kline_thread = threading.Thread(target=kline_updates.start_stream)
kline_thread.start()

# Research market updates
market_data_updates = MarketUpdates()
market_updates_thread = threading.Thread(target=market_data_updates.start_stream)
market_updates_thread.start()
