import os
from pymongo import MongoClient

def setup_db():
    # Database
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    db = mongo[os.getenv("MONGO_APP_DATABASE")]
    return db