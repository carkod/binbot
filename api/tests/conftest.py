from pytest import fixture
from typing import Generator
from fastapi.testclient import TestClient
from database.api_db import ApiDb
from main import app
from unittest.mock import MagicMock, patch

@fixture(scope="session")
def get_session_mock() -> Generator[MagicMock, None, None]:
    session_mock = MagicMock()
    exec_mock = MagicMock(return_value=True)
    session_mock.configure_mock(**{"exec.return_value": exec_mock})

    with (
        patch("sqlmodel.Session", return_value=session_mock),
    ):
        yield session_mock


@fixture(scope="session")
def client() -> TestClient:
    api_db = ApiDb()
    api_db.init_db()
    return TestClient(app)


@fixture(scope="session")
def mock_lifespan():
    with patch("main.lifespan") as mock_lifespan:
        yield mock_lifespan
