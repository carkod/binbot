import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            ("X-MBX-APIKEY", "DUMMY"),
            ("authorization", "DUMMY"),
        ],
    }


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
