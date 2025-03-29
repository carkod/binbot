from fastapi.testclient import TestClient
from main import app
from pytest import fixture, mark


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


test_symbol = "BOMEUSDC"
test_error_symbol = "BTCUSDT"


@mark.vcr("cassettes/get_all_symbols.yaml")
def test_get_all_symbols(client: TestClient):
    response = client.get("/symbols")

    content = response.json()
    assert content["data"][0] == {
        "created_at": 1742518873414,
        "updated_at": 1742518873414,
        "active": True,
        "is_margin_trading_allowed": True,
        "base_asset": "XRP",
        "qty_precision": 0,
        "cooldown": 0,
        "blacklist_reason": "",
        "id": "XRPUSDC",
        "quote_asset": "USDC",
        "price_precision": 4,
        "min_notional": 5.0,
        "cooldown_start_ts": 0,
    }


@mark.vcr("cassettes/test_one_symbol.yaml")
def test_one_symbol(client: TestClient):
    response = client.get(f"/symbol/{test_symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == {
        "created_at": 1742962001403,
        "updated_at": 1742962001403,
        "active": True,
        "is_margin_trading_allowed": False,
        "base_asset": "BOME",
        "qty_precision": 0,
        "cooldown": 0,
        "id": "BOMEUSDC",
        "blacklist_reason": "",
        "quote_asset": "USDC",
        "price_precision": 6,
        "min_notional": 1.0,
        "cooldown_start_ts": 0,
    }


@mark.vcr("cassettes/test_one_symbol_error.yaml")
def test_one_symbol_error(client: TestClient):
    response = client.get(f"/symbol/{test_error_symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] is None


@mark.vcr("cassettes/test_add_existing_symbol.yaml")
def test_add_existing_symbol(client: TestClient):
    payload = {
        "active": True,
        "blacklist_reason": "",
        "quote_asset": "USDC",
        "price_precision": 6,
        "min_notional": 1.0,
        "cooldown_start_ts": 0,
        "created_at": 1742518875379,
        "updated_at": 1742518875379,
        "id": "BOMEUSDC",
        "is_margin_trading_allowed": True,
        "base_asset": "BOME",
        "qty_precision": 0,
        "cooldown": 0,
    }
    response = client.post("/bot", json=payload)

    assert response.status_code == 422


@mark.vcr("cassettes/test_add_symbol.yaml")
def test_add_symbol(client: TestClient):
    payload = {
        "symbol": test_symbol,
        "active": "true",
        "blacklist_reason": "",
        "quote_asset": "USDC",
        "price_precision": "6",
        "min_notional": "1.0",
        "cooldown_start_ts": "0",
        "created_at": "1742518875379",
        "updated_at": "1742518875379",
        "id": "BOMEUSDC",
        "is_margin_trading_allowed": "true",
        "base_asset": "BOME",
        "qty_precision": "0",
        "cooldown": "0",
    }
    response = client.post("/symbol", params=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == {
        "created_at": 1742962001403,
        "updated_at": 1742962001403,
        "active": True,
        "is_margin_trading_allowed": False,
        "base_asset": "BOME",
        "qty_precision": 0,
        "cooldown": 0,
        "id": "BOMEUSDC",
        "blacklist_reason": "",
        "quote_asset": "USDC",
        "price_precision": 6,
        "min_notional": 1.0,
        "cooldown_start_ts": 0,
    }


@mark.vcr("cassettes/test_edit_symbol.yaml")
def test_edit_symbol(client: TestClient):
    payload = {
        "active": True,
        "blacklist_reason": "test blacklist reason",
        "quote_asset": "USDC",
        "price_precision": 6,
        "min_notional": 1.0,
        "cooldown_start_ts": 0,
        "created_at": 1742960362837,
        "updated_at": 1742960362837,
        "id": "BOMEUSDC",
        "is_margin_trading_allowed": True,
        "base_asset": "BOME",
        "qty_precision": 0,
        "cooldown": 0,
    }
    response = client.put(url="/symbol", json=payload)
    content = response.json()
    assert content["data"] == payload


@mark.vcr("cassettes/test_edit_bot.yaml")
def test_delete_symbol(client: TestClient):
    response = client.delete(f"/symbol/{test_symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Symbol deleted"
