import pytest
from unittest.mock import MagicMock, patch


from sqlmodel import SQLModel
from databases.utils import engine

# The import below is required to register all models for SQLModel metadata. Do not remove!
import databases.tables  # noqa: F401


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            ("X-MBX-APIKEY", "DUMMY"),
            ("authorization", "DUMMY"),
        ],
        "record_mode": "new_episodes",  # or use "all" to always re-record
    }


class MockAsyncBaseProducer:
    def __init__(self):
        pass

    def start_producer(self):
        producer = MagicMock()
        return producer

    def update_required(self, action):
        return action


# Ensure all tables are created before any tests run
@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    SQLModel.metadata.create_all(engine)
    yield
    # Optionally, drop tables after tests (uncomment if needed):
    # SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def mock_lifespan():
    with patch("main.lifespan") as mock_lifespan:
        yield mock_lifespan
