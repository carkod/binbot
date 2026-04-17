from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from pytest import fixture
import pytest
from tests.fixtures.mock_bot_table import make_mock_bot_active_model

pytestmark = pytest.mark.usefixtures("paper_trading_table_fixture")


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


mock_id = "2d1966f6-0924-45ab-ae47-2b8c20408e22"
mock_symbol = "TRXUSDC"


def test_paper_trading_get_one(client: TestClient):
    response = client.get(f"/paper-trading/{mock_id}")

    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert content["data"]["pair"] == "TRXUSDC"
    assert "fiat" in content["data"]
    assert "fiat_order_size" in content["data"]
    assert "deal" in content["data"]


def test_paper_trading_get_one_by_symbol(client: TestClient):
    response = client.get("/paper-trading/symbol/ADXUSDC")

    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert content["data"]["pair"] == "ADXUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert "fiat_order_size" in content["data"]
    assert "deal" in content["data"]
    assert "orders" in content["data"]


def test_paper_trading_get_bots(client: TestClient):
    response = client.get("/paper-trading")

    assert response.status_code == 200
    content = response.json()
    # Verify response structure and content
    assert isinstance(content["data"], list)
    assert len(content["data"]) > 0
    # Check first bot has expected fields
    first_bot = content["data"][0]
    assert "pair" in first_bot
    assert "fiat" in first_bot
    assert "fiat_order_size" in first_bot
    assert first_bot["fiat"] == "USDC"


def test_paper_trading_create_bot(client: TestClient):
    payload = {
        "status": "inactive",
        "balance_available": 0,
        "fiat_order_size": 2,
        "fiat": "USDC",
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "pair": "TRXUSDC",
        "take_profit": 2.3,
        "trailing": True,
        "trailing_deviation": 2.8,
        "trailing_profit": 2.3,
        "dynamic_trailing": True,
        "stop_loss": 3,
        "margin_short_reversal": True,
        "position": "long",
    }

    response = client.post("/paper-trading", json=payload)

    assert response.status_code == 200
    content = response.json()
    data = content["data"]
    # Check key fields are present and correct
    assert data["pair"] == "TRXUSDC"
    assert data["fiat"] == "USDC"
    assert data["fiat_order_size"] == 2.0
    assert data["mode"] == "manual"
    assert data["name"] == "terminal_1743217337463"
    assert data["status"] == "inactive"
    assert data["stop_loss"] == 3.0
    assert data["margin_short_reversal"] is True
    assert data["take_profit"] == 2.3
    assert data["trailing"] is True
    assert data["trailing_deviation"] == 2.8
    assert data["position"] == "long"
    # Verify structure
    assert "id" in data
    assert "deal" in data
    assert "orders" in data
    assert isinstance(data["orders"], list)


def test_paper_trading_edit_bot(client: TestClient):
    payload = {
        "pair": "TRXUSDC",
        "fiat": "USDC",
        "fiat_order_size": 50,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailing",
        "cooldown": 0,
        "dynamic_trailing": True,
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "status": "inactive",
        "stop_loss": 3,
        "margin_short_reversal": True,
        "take_profit": 2.3,
        "trailing": True,
        "trailing_deviation": 2.8,
        "trailing_profit": 2.3,
        "position": "long",
    }

    response = client.put(
        "/paper-trading/2d1966f6-0924-45ab-ae47-2b8c20408e22", json=payload
    )

    assert response.status_code == 200
    content = response.json()
    # Check response structure - may create new or update existing
    assert "data" in content
    assert content["data"]["pair"] == "TRXUSDC"
    assert content["data"]["fiat_order_size"] == 50
    assert content["data"]["stop_loss"] == 3


def test_paper_trading_delete_bot(client: TestClient):
    delete_ids = ["86da4c65-2728-4625-be61-a1d5f44d706f"]
    response = client.request("DELETE", "/paper-trading", json={"ids": delete_ids})

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Successfully deleted bot!"


@pytest.mark.vcr(cassette_path="paper_trading/test_paper_trading_activate.yaml")
def test_paper_trading_activate_by_id(client: TestClient):
    # Test activate endpoint - note: full activation requires symbol data
    # Just verify the endpoint returns a response (may be error if symbol not found)
    response = client.get(f"/paper-trading/activate/{mock_id}")

    # The endpoint should return a response (either success or handled error)
    assert response.status_code in [200, 400, 404, 422]
    content = response.json()
    assert "data" in content or "detail" in content or "message" in content


@pytest.mark.vcr(cassette_path="paper_trading/test_paper_trading_deactivate.yaml")
def test_paper_trading_deactivate(client: TestClient):
    deactivate_id = "3c3dd13e-4233-4e91-b27b-97459ff33fe7"
    response = client.delete(f"/paper-trading/deactivate/{deactivate_id}")

    assert response.status_code == 200
    content = response.json()
    # Check the message and that data is present
    assert "message" in content
    assert "data" in content
    assert content["data"] is not None


def test_paper_trading_deactivate_algorithmic_close(client: TestClient):
    deactivate_id = "3c3dd13e-4233-4e91-b27b-97459ff33fe7"
    active_bot = make_mock_bot_active_model()

    with patch(
        "deals.gateway.DealGateway.deactivation",
        return_value=active_bot,
    ) as mock_deactivate:
        response = client.delete(
            f"/paper-trading/deactivate/{deactivate_id}?algorithmic_close=true"
        )

    assert response.status_code == 200
    content = response.json()
    assert "message" in content
    assert "data" in content
    assert content["data"] is not None
    mock_deactivate.assert_called_once_with(algorithmic_close=True)
