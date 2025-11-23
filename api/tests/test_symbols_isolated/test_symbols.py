import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


test_symbol = "GASBTC"
test_new_symbol = "NEWUSDC"


def test_get_all_symbols(client: TestClient):
    # Test filter by active=True
    response = client.get("/symbols", params={"active": True})
    content = response.json()
    assert all(item["active"] is True for item in content["data"])

    # Test filter by active=False
    response = client.get("/symbols", params={"active": False})
    content = response.json()
    assert all(item["active"] is False for item in content["data"])

    # Test no filters (should return all symbols)
    response = client.get("/symbols")
    content = response.json()
    assert isinstance(content["data"], list)


def test_one_symbol(client: TestClient):
    symbol = "GASBTC"
    response = client.get(f"/symbol/{symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["id"] == "GASBTC"
    assert content["data"]["base_asset"] == ""
    assert content["data"]["quote_asset"] == ""
    assert content["data"]["active"] is True
    assert content["data"]["price_precision"] == 7
    assert content["data"]["qty_precision"] == 1
    assert content["data"]["is_margin_trading_allowed"] is False


def test_get_one_symbol_not_found(client: TestClient):
    response = client.get("/symbol/BBTCUSDC")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Symbol not found"
    assert content["error"] == 1


def test_one_symbol_error(client: TestClient):
    # Test with non-existent symbol
    response = client.get("/symbol/NONEXISTENT")

    assert response.status_code == 200
    content = response.json()
    assert content["error"] == 1
    assert content["message"] == "Symbol not found"


def test_add_symbol(client: TestClient):
    response = client.post(
        "/symbol",
        params={
            "symbol": test_new_symbol,
            "quote_asset": "USDC",
            "base_asset": "NEW",
            "min_notional": 1.0,
            "price_precision": 6,
            "qty_precision": 2,
            "active": True,
        },
    )

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Symbols found!"
    assert content["data"]["id"] == test_new_symbol


def test_delete_symbol(client: TestClient):
    # Delete LRCBTC which exists in fixtures
    response = client.delete("/symbol/LRCBTC")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Symbol deleted"


def test_edit_symbol(client: TestClient):
    payload = {
        "active": False,
        "blacklist_reason": "test blacklist reason",
        "quote_asset": "BTC",
        "price_precision": 7,
        "min_notional": 0.0001,
        "cooldown_start_ts": 0,
        "id": test_symbol,
        "exchange_id": "binance",
        "symbol_id": test_symbol,
        "is_margin_trading_allowed": False,
        "base_asset": "GAS",
        "qty_precision": 1,
        "cooldown": 0,
        "asset_indices": [],
    }
    response = client.put(url="/symbol", json=payload)
    assert response.status_code == 200
    content = response.json()
    assert content["data"]["blacklist_reason"] == "test blacklist reason"
    assert content["data"]["active"] is False
