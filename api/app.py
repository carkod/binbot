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
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD")
    )
    app.db = mongo[os.getenv("MONGO_APP_DATABASE")]
    
    # if "bots" not in app.db.list_collection_names():
    #     app.db.create_collection("bots")

    # # Set default indexes for db
    # app.db.bots.create_index([
    #     ("pair", ASCENDING)
    # ])
    
    return app
