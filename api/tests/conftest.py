from pytest import fixture
from unittest.mock import MagicMock, patch


class MockAsyncBaseProducer:
    def __init__(self):
        pass

    def start_producer(self):
        producer = MagicMock()
        return producer

    def update_required(self, action):
        return action


@fixture(scope="session")
def mock_lifespan():
    with patch("main.lifespan") as mock_lifespan:
        yield mock_lifespan
