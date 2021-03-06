from api.orders.models.order_sockets import OrderUpdates
import os
import atexit

from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mongoengine import MongoEngine
import threading
import time
import logging

# Import Routes
from api.account.models import Assets
from api.orders.models.orders import Orders
from api.tools.jsonresp import jsonResp
from api.user.routes import user_blueprint
from api.account.routes import account_blueprint
from api.bots.routes import bot_blueprint
from api.deals.routes import deal_blueprint
from api.orders.routes import order_blueprint
from api.charts.routes import charts_blueprint

app = Flask(__name__)
# Schema
# db = MongoEngine(app)
# Enable CORS for all routes
CORS(app)
# Misc Config
os.environ["TZ"] = os.environ["TIMEZONE"]

mongo = MongoClient(os.environ["MONGO_HOSTNAME"], int(os.environ["MONGO_PORT"]))
mongo[os.environ["MONGO_AUTH_DATABASE"]].authenticate(
    os.environ["MONGO_AUTH_USERNAME"], os.environ["MONGO_AUTH_PASSWORD"]
)
app.db = mongo[os.environ["MONGO_APP_DATABASE"]]

# Cronjob
scheduler = BackgroundScheduler()
assets = Assets(app)
orders = Orders(app)

scheduler.add_job(
    func=assets.store_balance, trigger="cron", timezone="Europe/London", hour=0, minute=1
)
scheduler.add_job(
    func=orders.poll_historical_orders,
    trigger="cron",
    args=[app],
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

# Index Route
@app.route("/")
def index():
    return jsonResp({"status": "Online"}, 200)


order_updates = OrderUpdates(app)
# start a worker process to move the received stream_data from the stream_buffer to a print function
worker_thread = threading.Thread(target=order_updates.get_stream)
worker_thread.start()
