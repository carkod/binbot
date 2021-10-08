import os
from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient, errors

def create_app():
    app = Flask(__name__)

    # Schema
    # db = MongoEngine(app)
    # Enable CORS for all routes
    CORS(app)
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD")
    )
    app.db = mongo[os.getenv("MONGO_APP_DATABASE")]

    # Setup collections
    if os.getenv("ENV") != "ci":
        if "blacklist" not in app.db.list_collection_names():
            app.db.create_collection("blacklist")
        
        if "research_controller" not in app.db.list_collection_names():
            app.db.create_collection("research_controller")
            app.db.insert({
                "_id": "settings",
                "candlestick_interval": "1h",
                "autotrade": 0,
                "errors": []
            })

    return app
