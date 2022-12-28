import os
from pymongo import MongoClient

def setup_db(host=os.getenv("MONGO_HOSTNAME"), port=int(os.getenv("MONGO_PORT"))):
    # Database
    mongo = MongoClient(
        host=host,
        port=port,
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    db = mongo[os.getenv("MONGO_APP_DATABASE")]
    return db