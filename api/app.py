import os
from flask import Flask
from flask_cors import CORS
from pymongo import ASCENDING, MongoClient, errors
from urllib.parse import quote_plus

def create_app():
    app = Flask(__name__)

    # Schema
    # db = MongoEngine(app)
    # Enable CORS for all routes
    CORS(app)
    try:
        mongo = MongoClient(host=os.getenv("MONGO_HOSTNAME"), port=int(os.getenv("MONGO_PORT")))
    except errors.ConnectionFailure as mongo_error:
        raise mongo_error

    app.db = mongo
    if os.getenv("ENV") != "ci":
        mongo[os.getenv("MONGO_AUTH_DATABASE")].authenticate(
            quote_plus(os.getenv("MONGO_AUTH_USERNAME")), quote_plus(os.getenv("MONGO_AUTH_PASSWORD"))
        )
        app.db = mongo[os.getenv("MONGO_APP_DATABASE")]
        # Set default indexes for db
        app.db.bots.create_index([
            ("pair", ASCENDING)
        ])

    return app
