from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from database.utils import get_session
from main import app
from pytest import fixture
from tests.model_mocks import (
    mock_model_data,
    id,
    mock_model_data_without_orders,
    CreateDealControllerMock,
)
from tests.table_mocks import mocked_db_data
from fastapi.encoders import jsonable_encoder


@fixture()
def client(pairs=False) -> TestClient:
    session_mock = MagicMock()
    session_mock.exec.return_value.first.return_value = mocked_db_data
    session_mock.exec.return_value.all.return_value = [mocked_db_data]
    session_mock.get.return_value = mocked_db_data
    session_mock.add.return_value = MagicMock(return_value=None)
    session_mock.refresh.return_value = MagicMock(return_value=None)
    session_mock.commit.return_value = MagicMock(return_value=None)
    app.dependency_overrides[get_session] = lambda: session_mock
    client = TestClient(app)
    return client


def test_get_one_by_id(client: TestClient):
    response = client.get(f"/bot/{id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == jsonable_encoder(mock_model_data.model_dump())


def test_get_one_by_symbol(client: TestClient):
    symbol = "ADXUSDC"
    response = client.get(f"/bot/symbol/{symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == jsonable_encoder(mock_model_data.model_dump())


def test_get_bots(client: TestClient):
    response = client.get("/bot")

    assert response.status_code == 200
    content = response.json()
    mock_data = jsonable_encoder(mock_model_data.model_dump())
    # Avoid testing internal objects
    assert content["data"] == [mock_data]


def test_create_bot(client: TestClient):
    payload = {
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "base_order_size": 15,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 360,
        "created_at": 1733973560249.0,
        "updated_at": 1733973560249.0,
        "dynamic_trailling": False,
        "logs": [],
        "mode": "manual",
        "name": "Default bot",
        "status": "inactive",
        "stop_loss": 3.0,
        "margin_short_reversal": False,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 3.0,
        "trailling_profit": 0.0,
        "strategy": "long",
        "total_commission": 0.0,
    }

    response = client.post("/bot", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mock_model_data_without_orders.model_dump()


def test_edit_bot(client: TestClient):
    payload = {
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "base_order_size": 15,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 360,
        "created_at": 1733973560249.0,
        "updated_at": 1733973560249.0,
        "dynamic_trailling": False,
        "logs": [],
        "mode": "manual",
        "name": "coinrule_fast_and_slow_macd_2024-04-20T22:28",
        "status": "inactive",
        "stop_loss": 3.0,
        "margin_short_reversal": False,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 3.0,
        "trailling_profit": 0.0,
        "strategy": "long",
        "total_commission": 0.0,
    }

    response = client.put(f"/bot/{id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == jsonable_encoder(mock_model_data.model_dump())


def test_delete_bot():
    # Fix missing json arg for delete tests
    class CustomTestClient(TestClient):
        def delete_with_payload(self, **kwargs):
            return self.request(method="DELETE", **kwargs)

    client = CustomTestClient(app)
    payload = [id]
    response = client.delete_with_payload(url="/bot", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Sucessfully deleted bot."


@patch("bots.routes.CreateDealController", CreateDealControllerMock)
def test_activate_by_id(client: TestClient):
    response = client.get(f"/bot/activate/{id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mock_model_data.model_dump()


@patch("bots.routes.CreateDealController", CreateDealControllerMock)
def test_deactivate(client: TestClient):
    response = client.delete(f"/bot/deactivate/{id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mock_model_data.model_dump()


def test_post_bot_errors_str(client: TestClient):
    """
    Test submitting bot errors with a single string
    """
    payload = {"errors": "failed to create bot"}

    response = client.post(f"/bot/errors/{id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."


def test_post_bot_errors_list(client: TestClient):
    """
    Test submitting bot errors with a list of strings
    """
    payload = {"errors": ["failed to create bot", "failed to create deal"]}

    response = client.post(f"/bot/errors/{id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."
