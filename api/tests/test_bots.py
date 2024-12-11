from uuid import uuid4
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from pytest import fixture
from database.models.bot_table import BotTable
from database.utils import get_session
from main import app
from unittest.mock import patch

id = uuid4()
ts = 1733973560249.0

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


@fixture()
def client() -> TestClient:
    session_mock = MagicMock()
    session_mock.exec.return_value.first.return_value = mocked_db_data
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
    for item in content["data"]:
        if item not in ["updated_at", "created_at", "id", "orders", "deal", "logs"]:
            assert content["data"][item] == mocked_db_data.__getattribute__(item)


def test_get_one_by_id(client: TestClient):
    test_id = "02031768-fbb9-4cc7-b549-642f15ab787b"
    response = client.get(f"/bot/{test_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump_json()


def test_get_one_by_symbol(client: TestClient):
    symbol = "ADXUSDC"
    response = client.get(f"/bot/{symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == mocked_db_data.model_dump_json()


# def test_active_pairs(patch_active_pairs):
#     client = TestClient(app)
#     response = client.get("/bot/active-pairs")

#     # Assert the expected result
#     expected_result = patch_active_pairs

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == expected_result
