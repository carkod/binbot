from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from database.utils import get_session
from main import app
from pytest import fixture
from tests.model_mocks import (
    active_pairs,
)
from tests.table_mocks import mocked_db_data


# @fixture()
# def client() -> TestClient:
#     # session_mock = MagicMock()
#     # session_mock.exec.return_value.first.return_value = mocked_db_data
#     # session_mock.exec.return_value.all.return_value = [mocked_db_data]
#     # session_mock.get.return_value = mocked_db_data
#     # session_mock.add.return_value = MagicMock(return_value=None)
#     # session_mock.refresh.return_value = MagicMock(return_value=None)
#     # session_mock.commit.return_value = MagicMock(return_value=None)
#     # app.dependency_overrides.clear()
#     # app.dependency_overrides[get_session] = lambda: session_mock
#     client = TestClient(app)
#     return client


def test_active_pairs():
    client = TestClient(app)
    response = client.get("/bot/active-pairs")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == active_pairs
