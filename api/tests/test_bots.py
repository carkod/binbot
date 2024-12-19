from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from pytest import fixture
from tools.enum_definitions import DealType, OrderType
from database.models import OrderModel
from database.models.bot_table import BotTable
from database.utils import get_session
from main import app
from unittest.mock import patch

id = "02031768-fbb9-4cc7-b549-642f15ab787b"
ts = 1733973560249.0

active_pairs = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

orders = [
    OrderModel(
        id=1,
        order_id=123,
        order_type=OrderType.market,
        time_in_force="GTC",
        timestamp=0,
        order_side="buy",
        pair="BTCUSDT",
        qty=0.000123,
        status="filled",
        price=1.222,
        deal_type=DealType.base_order,
        total_commission=0,
    ),
    OrderModel(
        id=2,
        order_id=321,
        order_type=OrderType.limit,
        time_in_force="GTC",
        timestamp=0,
        order_side="sell",
        pair="BTCUSDT",
        qty=0.000123,
        status="filled",
        price=1.222,
        deal_type=DealType.take_profit,
        total_commission=0,
    ),
]

mocked_db_data = BotTable(
    id=id,
    pair="ADXUSDC",
    fiat="USDC",
    base_order_size=50,
    candlestick_interval="15m",
    close_condition="dynamic_trailling",
    cooldown=360,
    created_at=ts,
    logs=[],
    mode="manual",
    name="coinrule_fast_and_slow_macd_2024-04-20T22:28",
    orders=[],
    stop_loss=3.0,
    take_profit=2.3,
    trailling=True,
    trailling_deviation=3.0,
    trailling_profit=0.0,
    strategy="long",
    updated_at=ts,
)

CreateDealControllerMock = MagicMock()
CreateDealControllerMock.return_value = MagicMock()
CreateDealControllerMock.return_value.open_deal.return_value = mocked_db_data


@fixture()
def client(pairs=False) -> TestClient:
    session_mock = MagicMock()
    session_mock.exec.return_value.first.return_value = mocked_db_data
    session_mock.exec.return_value.all.return_value = [mocked_db_data]
    session_mock.get.return_value = mocked_db_data
    session_mock.add.return_value = MagicMock(return_value=None)
    session_mock.commit.return_value = MagicMock(return_value=None)
    app.dependency_overrides[get_session] = lambda: session_mock
    client = TestClient(app)
    return client


@patch("database.models.bot_table.timestamp", lambda: ts)
def test_create_bot(client: TestClient):
    payload = {
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "base_order_size": 50,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 360,
        "mode": "manual",
        "name": "coinrule_fast_and_slow_macd_2024-04-20T22:28",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 3.0,
        "trailling_profit": 0.0,
        "strategy": "long",
    }

    response = client.post("/bot", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump()


def test_get_one_by_id(client: TestClient):
    response = client.get(f"/bot/{id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump()


def test_get_one_by_symbol(client: TestClient):
    symbol = "ADXUSDC"
    response = client.get(f"/bot/symbol/{symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump()


def test_get_bots(client: TestClient):
    response = client.get("/bot")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == [mocked_db_data.model_dump()]


def test_edit_bot(client: TestClient):
    payload = {
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "base_order_size": 50,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 360,
        "mode": "manual",
        "name": "coinrule_fast_and_slow_macd_2024-04-20T22:28",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 3.0,
        "trailling_profit": 0.0,
        "strategy": "long",
    }

    response = client.put(f"/bot/{id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump()


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
    assert content["message"] == "Bots deleted successfully."


@patch("bots.routes.CreateDealController", CreateDealControllerMock)
def test_activate_by_id(client: TestClient):
    response = client.get(f"/bot/activate/{id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump()


def test_active_pairs():
    # Only endpoint to not return a bot
    session_mock = MagicMock()
    session_mock.exec.return_value.all.return_value = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
    session_mock.commit.return_value = MagicMock(return_value=None)
    app.dependency_overrides[get_session] = lambda: session_mock
    test_client = TestClient(app)

    response = test_client.get("/bot/active-pairs")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == active_pairs


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
    payload = {"errors": ["failed to create bot", "failed to create bot"]}

    response = client.post(f"/bot/errors/{id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."
