from cgi import test
from fastapi.testclient import TestClient
from httpx import patch
import pytest
from bots.controllers import Bot
from main import app
import mongomock


@pytest.fixture()
def patch_bot(monkeypatch):
    bot = {
        "id": "6624255433c3cf9806d0a70e",
        "pair": "ADXUSDT",
        "balance_size_to_use": "0.0",
        "balance_to_use": "USDT",
        "base_order_size": "50",
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 360,
        "created_at": 1713643305854.368,
        "deal": {
            "buy_price": 0.2257,
            "base_order_price": 0.0,
            "buy_timestamp": 1713644889534.0,
            "buy_total_qty": 221.0,
        },
        "errors": [],
        "mode": "autotrade",
        "name": "coinrule_fast_and_slow_macd_2024-04-20T22:28",
        "orders": [
            {
                "order_type": "LIMIT",
                "time_in_force": "GTC",
                "timestamp": 1713644889534.0,
                "pair": "ADXUSDT",
                "qty": "221.00000000",
                "order_side": "BUY",
                "order_id": 1,
                "fills": [],
                "price": 0.2257,
                "status": "NEW",
                "deal_type": "base_order",
            }
        ],
        "status": "active",
        "stop_loss": 3.0,
        "take_profit": 2.3,
        "trailling": "true",
        "trailling_deviation": 3.0,
        "trailling_profit": 0.0,
        "strategy": "long",
        "updated_at": 1713643305854.435,
    }

    def new_init(self, collection_name="bots"):
        mongo_client = mongomock.MongoClient()
        self.db = mongo_client.db
        self.db_collection = self.db[collection_name]

    monkeypatch.setattr(Bot, "__init__", new_init)
    monkeypatch.setattr(Bot, "get_one", lambda self, bot_id, symbol: bot)

    return bot

@pytest.fixture()
def patch_active_pairs(monkeypatch):
    active_pairs = ["BNBUSDT", "BTCUSDT"]

    def new_init(self, collection_name="bots"):
        mongo_client = mongomock.MongoClient()
        self.db = mongo_client.db
        self.db_collection = self.db[collection_name]

    monkeypatch.setattr(Bot, "__init__", new_init)
    monkeypatch.setattr(Bot, "get_active_pairs", lambda self: active_pairs)

    return active_pairs

def test_get_one_by_id(patch_bot):
    client = TestClient(app)
    test_id = "6624255433c3cf9806d0a70e"
    response = client.get(f"/bot/{test_id}")

    # Assert the expected result
    expected_result = patch_bot

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == expected_result

def test_get_one_by_symbol(patch_bot):
    client = TestClient(app)
    symbol = "ADXUSDT"
    response = client.get(f"/bot/{symbol}")

    # Assert the expected result
    expected_result = patch_bot

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == expected_result

def test_active_pairs(patch_active_pairs):
    client = TestClient(app)
    response = client.get(f"/bot/active-pairs")

    # Assert the expected result
    expected_result = patch_active_pairs

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == expected_result
