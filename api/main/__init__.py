from flask import Flask
from pymongo import MongoClient
import os
from main.tools.jsonresp import jsonResp
from flask_cors import CORS
import atexit

from apscheduler.schedulers.background import BackgroundScheduler
from main.account.models import Assets

# Import Routes
from main.user.routes import user_blueprint
from main.account.routes import account_blueprint
from main.bots.routes import bot_blueprint
from main.deals.routes import deal_blueprint
from main.orders.routes import order_blueprint
from main.charts.routes import charts_blueprint

def create_app():

    # Flask Config
    app = Flask(__name__)
    # Enable CORS for all routes
    CORS(app)
    # Misc Config
    os.environ["TZ"] = os.environ["TIMEZONE"]

    mongo = MongoClient(os.environ["MONGO_HOSTNAME"], int(os.environ["MONGO_PORT"]))
    mongo[os.environ["MONGO_AUTH_DATABASE"]].authenticate(os.environ["MONGO_AUTH_USERNAME"], os.environ["MONGO_AUTH_PASSWORD"])
    app.db = mongo[os.environ["MONGO_APP_DATABASE"]]

    # Cronjob
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=Assets().store_balance, trigger="cron", hour="21", minute="0")
    scheduler.start()
    # Shut down the scheduler when exiting the app
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

    return app
