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


@mark.vcr("cassettes/get_all_symbols_index.yaml")
def test_get_all_symbols_index_filters(client: TestClient):
    # Test filter by index only (assuming 'defi' is a valid index id in your test data)
    index_id = "defi"
    response = client.get("/symbols", params={"index": index_id})
    content = response.json()
    # All returned symbols should have the index in their asset_indices
    for symbol in content["data"]:
        assert any(idx["id"] == index_id for idx in symbol.get("asset_indices", []))

    # Test filter by index and active=False (should return all symbols with the index, regardless of active)
    response = client.get("/symbols", params={"index": index_id, "active": False})
    content = response.json()
    for symbol in content["data"]:
        assert any(idx["id"] == index_id for idx in symbol.get("asset_indices", []))


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


@mark.vcr("cassettes/test_update_indexes.yaml")
def test_update_indexes(client: TestClient):
    payload = {"id": "DOGEUSDC", "asset_indeces": [{"id": "meme", "name": "Meme coin"}]}
    response = client.put("/symbol/asset-index", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Symbol asset index updated"
    assert data["data"] is not None


test_symbol = "BOMEUSDC"
test_error_symbol = "BTCUSDT"
