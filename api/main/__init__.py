from flask import Flask
from pymongo import MongoClient
import os
import json
from flask_cors import CORS
# Import Routes
from main.user.routes import user_blueprint
from main.account.routes import account_blueprint
from main.bots.routes import bot_blueprint
from main.deals.routes import deal_blueprint
from main.orders.routes import order_blueprint

def create_app():

    # Flask Config
    app = Flask(__name__)
    # Enable CORS for all routes
    CORS(app)
    # Misc Config
    os.environ["TZ"] = os.environ["TIMEZONE"]

    # Database Config
    # if  os.environ["ENVIRONMENT"] == "development":
    # mongo = MongoClient( os.environ["MONGO_HOSTNAME"],  os.environ["MONGO_PORT"])
    # app.db = mongo[ os.environ["MONGO_APP_DATABASE"]]
    # else:
    #   mongo = MongoClient("localhost")
    #   mongo[ os.environ["MONGO_AUTH_DATABASE"]].authenticate( os.environ["MONGO_AUTH_USERNAME"],  os.environ["MONGO_AUTH_PASSWORD"])
    #   app.db = mongo[ os.environ["MONGO_APP_DATABASE"]]

    mongo = MongoClient(os.environ["MONGO_HOSTNAME"], int(os.environ["MONGO_PORT"]))
    mongo[os.environ["MONGO_AUTH_DATABASE"]].authenticate(os.environ["MONGO_AUTH_USERNAME"], os.environ["MONGO_AUTH_PASSWORD"])
    app.db = mongo[os.environ["MONGO_APP_DATABASE"]]

    # Register Blueprints
    app.register_blueprint(user_blueprint, url_prefix="/user")
    app.register_blueprint(account_blueprint, url_prefix="/account")
    app.register_blueprint(bot_blueprint, url_prefix="/bot")
    app.register_blueprint(deal_blueprint, url_prefix="/deal")
    app.register_blueprint(order_blueprint, url_prefix="/order")

    # Index Route
    @app.route("/")
    def index():
        return json.dumps({"status": "Online"}, 200)

    return app
