import os
from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
from api.apis import BinanceApi, CoinBaseApi

def create_app():
    app = Flask(__name__)

    # Schema
    # db = MongoEngine(app)
    # Enable CORS for all routes
    CORS(app)
    mongo = MongoClient(os.environ["MONGO_HOSTNAME"], int(os.environ["MONGO_PORT"]))
    mongo[os.environ["MONGO_AUTH_DATABASE"]].authenticate(
        os.environ["MONGO_AUTH_USERNAME"], os.environ["MONGO_AUTH_PASSWORD"]
    )
    app.db = mongo[os.environ["MONGO_APP_DATABASE"]]

    return app
