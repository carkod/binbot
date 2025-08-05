import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True, scope="session")
def mock_settings_env():
    env = {
        "PIPENV_VENV_IN_PROJECT": "1",
        "PYTHONUNBUFFERED": "0",
        "DEBUG": "True",
        "LOG_LEVEL": "ERROR",
        "SECRET_KEY": "dev_key",
        "ENV": "development",
        "FLASK_DIRECTORY": "/api/",
        "FLASK_DOMAIN": "http://localhost:8008",
        "FRONTEND_DOMAIN": "http://localhost:3000",
        "HTTP_HTTPS": "http://",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "525600",
        "MONGO_HOSTNAME": "localhost",
        "MONGO_PORT": "27018",
        "MONGO_AUTH_DATABASE": "admin",
        "MONGO_AUTH_USERNAME": "carkod",
        "MONGO_AUTH_PASSWORD": "mongo",
        "MONGO_APP_DATABASE": "binbot",
        "MONGO_KAFKA_DATABASE": "kafka",
        "KAFKA_PORT": "9092",
        "KAFKA_HOST": "localhost",
        "POSTGRES_USER": "binbot",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": "binbot",
        "POSTGRES_HOSTNAME": "localhost",
        "USER": "carkod",
        "PASSWORD": "password",
        "BINANCE_KEY": "binance_fake_key",
        "BINANCE_SECRET": "binance_fake_secret",
        "TELEGRAM_BOT_KEY": "123",
        "TELEGRAM_USER_ID": "binbot",
        "GRAFANA_TOKEN": "fake_key",
    }
    old_env = os.environ.copy()
    os.environ.update(env)
    yield
    os.environ.clear()
    os.environ.update(old_env)


class MockAsyncBaseProducer:
    def __init__(self):
        pass

    def start_producer(self):
        producer = MagicMock()
        return producer

    def update_required(self, action):
        return action


@pytest.fixture(scope="session")
def mock_lifespan():
    with patch("main.lifespan") as mock_lifespan:
        yield mock_lifespan


@pytest.fixture(scope="module")
def vcr_config():
    return {
        # Replace the Authorization request header with "DUMMY" in cassettes
        "filter_headers": [("authorization", "DUMMY")],
    }
