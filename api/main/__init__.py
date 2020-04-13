import os

from flask_api import FlaskAPI, request

from jose import jwt
from main.account.routes import account_blueprint
from main.bots.routes import bot_blueprint
from main.deals.routes import deal_blueprint
from main.orders.routes import order_blueprint
from main.tools import JsonResp

# Import Routes
from main.user.routes import user_blueprint
from main.userDataStream.routes import user_datastream_blueprint
from pymongo import MongoClient
import os

def create_app():
    # Flask Config
    app = FlaskAPI(__name__)
    # cors = CORS(app, resources={r"/*": { "origins": os.environ["FRONTEND_DOMAIN"] }})
    mongo = MongoClient(os.environ["MONGO_HOSTNAME"], int(os.environ["MONGO_PORT"]))
    mongo[os.environ["MONGO_AUTH_DATABASE"]].authenticate(
        os.environ["MONGO_AUTH_USERNAME"], os.environ["MONGO_AUTH_PASSWORD"]
    )
    app.db = mongo[os.environ["MONGO_APP_DATABASE"]]
    root_route = "/api/v1/"


    # Register Blueprints
    app.register_blueprint(user_blueprint, url_prefix=f"{root_route}user")
    app.register_blueprint(account_blueprint, url_prefix=f"{root_route}account")
    app.register_blueprint(bot_blueprint, url_prefix=f"{root_route}bot")
    app.register_blueprint(deal_blueprint, url_prefix=f"{root_route}deal")
    app.register_blueprint(order_blueprint, url_prefix=f"{root_route}order")
    app.register_blueprint(user_datastream_blueprint, url_prefix=f"{root_route}user-data-stream")

    # Index Route
    @app.route(f"{root_route}")
    def index():
        return JsonResp({"status": "Online"}, 200)

    return app
