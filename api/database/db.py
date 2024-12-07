import os
from pymongo import MongoClient


def get_mongo_client():
    client: MongoClient = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT", 27018)),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    return client


def setup_db():
    # Database
    mongo = get_mongo_client()
    db = mongo[os.getenv("MONGO_APP_DATABASE", "app")]
    return db


def setup_kafka_db():
    # Time series optimized database
    mongo = get_mongo_client()
    db = mongo[os.getenv("MONGO_KAFKA_DATABASE", "kafka")]
    return db


class Database:
    """
    The whole objective of having this class is to provide
    a single point of entry to the database.
    Therefore, always initialize database instance

    Methods in this should only be helpers
    that can be independently triggered, where
    only dependency is the _db instance
    """

    _db = setup_db()
    kafka_db = setup_kafka_db()
