import os
from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient


def create_app():
    app = Flask(__name__)

    # Schema
    # db = MongoEngine(app)
    # Enable CORS for all routes
    CORS(app, expose_headers="Authorization")
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    app.db = mongo[os.getenv("MONGO_APP_DATABASE")]

    return app
