"""
Test authentication for all API endpoints.

This test suite verifies that:
1. All protected endpoints require authentication
2. Endpoints return 401 when no token is provided
3. Endpoints return 401 when an invalid token is provided
4. Endpoints work correctly when a valid token is provided
"""

from fastapi.testclient import TestClient
from main import app
from pytest import fixture
from user.services.auth import create_access_token


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


@fixture()
def valid_token() -> str:
    """Create a valid JWT token for testing."""
    token, _ = create_access_token("test@example.com")
    return token


@fixture()
def auth_headers(valid_token: str) -> dict:
    """Create authorization headers with a valid token."""
    return {"Authorization": f"Bearer {valid_token}"}


# Bot endpoints
def test_get_bots_requires_auth(client: TestClient):
    """Test that GET /bot requires authentication."""
    response = client.get("/bot")
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert "Not authenticated" in detail or "Could not validate credentials" in detail


def test_get_bots_with_valid_token(client: TestClient, auth_headers: dict):
    """Test that GET /bot works with valid authentication."""
    response = client.get("/bot", headers=auth_headers)
    # Should succeed or return a proper error (not 401)
    assert response.status_code != 401


def test_get_bot_by_id_requires_auth(client: TestClient):
    """Test that GET /bot/{id} requires authentication."""
    response = client.get("/bot/some-id")
    assert response.status_code == 401


def test_get_bot_by_id_with_valid_token(client: TestClient, auth_headers: dict):
    """Test that GET /bot/{id} works with valid authentication."""
    response = client.get("/bot/some-id", headers=auth_headers)
    assert response.status_code != 401


def test_create_bot_requires_auth(client: TestClient):
    """Test that POST /bot requires authentication."""
    response = client.post("/bot", json={"pair": "BTCUSDT"})
    assert response.status_code == 401


def test_update_bot_requires_auth(client: TestClient):
    """Test that PUT /bot/{id} requires authentication."""
    response = client.put("/bot/some-id", json={"pair": "BTCUSDT"})
    assert response.status_code == 401


def test_delete_bot_requires_auth(client: TestClient):
    """Test that DELETE /bot requires authentication."""
    response = client.delete("/bot", params={"id": ["some-id"]})
    assert response.status_code == 401


def test_activate_bot_requires_auth(client: TestClient):
    """Test that GET /bot/activate/{id} requires authentication."""
    response = client.get("/bot/activate/some-id")
    assert response.status_code == 401


def test_deactivate_bot_requires_auth(client: TestClient):
    """Test that DELETE /bot/deactivate/{id} requires authentication."""
    response = client.delete("/bot/deactivate/some-id")
    assert response.status_code == 401


# Account endpoints
def test_get_balance_requires_auth(client: TestClient):
    """Test that GET /account/balance/raw requires authentication."""
    response = client.get("/account/balance/raw")
    assert response.status_code == 401


def test_get_balance_with_valid_token(client: TestClient, auth_headers: dict):
    """Test that GET /account/balance/raw works with valid authentication."""
    response = client.get("/account/balance/raw", headers=auth_headers)
    assert response.status_code != 401


def test_get_balance_estimate_requires_auth(client: TestClient):
    """Test that GET /account/balance/estimate requires authentication."""
    response = client.get("/account/balance/estimate")
    assert response.status_code == 401


def test_get_pnl_requires_auth(client: TestClient):
    """Test that GET /account/pnl requires authentication."""
    response = client.get("/account/pnl")
    assert response.status_code == 401


def test_store_balance_requires_auth(client: TestClient):
    """Test that GET /account/store-balance requires authentication."""
    response = client.get("/account/store-balance")
    assert response.status_code == 401


def test_gainers_losers_requires_auth(client: TestClient):
    """Test that GET /account/gainers-losers requires authentication."""
    response = client.get("/account/gainers-losers")
    assert response.status_code == 401


def test_balance_series_requires_auth(client: TestClient):
    """Test that GET /account/balance-series requires authentication."""
    response = client.get("/account/balance-series")
    assert response.status_code == 401


def test_clean_balance_requires_auth(client: TestClient):
    """Test that GET /account/clean requires authentication."""
    response = client.get("/account/clean")
    assert response.status_code == 401


def test_fiat_available_requires_auth(client: TestClient):
    """Test that GET /account/fiat/available requires authentication."""
    response = client.get("/account/fiat/available")
    assert response.status_code == 401


def test_fiat_requires_auth(client: TestClient):
    """Test that GET /account/fiat requires authentication."""
    response = client.get("/account/fiat")
    assert response.status_code == 401


# Order endpoints
def test_buy_order_requires_auth(client: TestClient):
    """Test that POST /order/buy requires authentication."""
    response = client.post("/order/buy", json={"pair": "BTCUSDT", "qty": 0.001})
    assert response.status_code == 401


def test_sell_order_requires_auth(client: TestClient):
    """Test that POST /order/sell requires authentication."""
    response = client.post("/order/sell", json={"pair": "BTCUSDT", "qty": 0.001})
    assert response.status_code == 401


def test_delete_order_requires_auth(client: TestClient):
    """Test that DELETE /order/close/{symbol}/{orderid} requires authentication."""
    response = client.delete("/order/close/BTCUSDT/123456")
    assert response.status_code == 401


def test_get_all_orders_requires_auth(client: TestClient):
    """Test that GET /order/all-orders requires authentication."""
    response = client.get("/order/all-orders?symbol=BTCUSDT")
    assert response.status_code == 401


# Symbols endpoints
def test_get_symbols_requires_auth(client: TestClient):
    """Test that GET /symbols requires authentication."""
    response = client.get("/symbols")
    assert response.status_code == 401


def test_get_symbols_with_valid_token(client: TestClient, auth_headers: dict):
    """Test that GET /symbols works with valid authentication."""
    response = client.get("/symbols", headers=auth_headers)
    assert response.status_code != 401


def test_get_symbol_requires_auth(client: TestClient):
    """Test that GET /symbol/{pair} requires authentication."""
    response = client.get("/symbol/BTCUSDT")
    assert response.status_code == 401


def test_add_symbol_requires_auth(client: TestClient):
    """Test that POST /symbol requires authentication."""
    response = client.post(
        "/symbol",
        params={
            "symbol": "BTCUSDT",
            "quote_asset": "USDT",
            "base_asset": "BTC",
        },
    )
    assert response.status_code == 401


def test_edit_symbol_requires_auth(client: TestClient):
    """Test that PUT /symbol requires authentication."""
    response = client.put("/symbol", json={"symbol": "BTCUSDT"})
    assert response.status_code == 401


def test_delete_symbol_requires_auth(client: TestClient):
    """Test that DELETE /symbol/{pair} requires authentication."""
    response = client.delete("/symbol/BTCUSDT")
    assert response.status_code == 401


# Paper trading endpoints
def test_get_paper_trading_requires_auth(client: TestClient):
    """Test that GET /paper-trading requires authentication."""
    response = client.get("/paper-trading")
    assert response.status_code == 401


def test_create_paper_trading_requires_auth(client: TestClient):
    """Test that POST /paper-trading requires authentication."""
    response = client.post("/paper-trading", json={"pair": "BTCUSDT"})
    assert response.status_code == 401


def test_update_paper_trading_requires_auth(client: TestClient):
    """Test that PUT /paper-trading/{id} requires authentication."""
    response = client.put("/paper-trading/some-id", json={"pair": "BTCUSDT"})
    assert response.status_code == 401


def test_delete_paper_trading_requires_auth(client: TestClient):
    """Test that DELETE /paper-trading requires authentication."""
    response = client.delete("/paper-trading", params={"id": ["some-id"]})
    assert response.status_code == 401


def test_activate_paper_trading_requires_auth(client: TestClient):
    """Test that GET /paper-trading/activate/{id} requires authentication."""
    response = client.get("/paper-trading/activate/some-id")
    assert response.status_code == 401


# Autotrade settings endpoints
def test_get_autotrade_settings_requires_auth(client: TestClient):
    """Test that GET /autotrade-settings/bots requires authentication."""
    response = client.get("/autotrade-settings/bots")
    assert response.status_code == 401


def test_get_autotrade_settings_with_valid_token(
    client: TestClient, auth_headers: dict
):
    """Test that GET /autotrade-settings/bots works with valid authentication."""
    response = client.get("/autotrade-settings/bots", headers=auth_headers)
    assert response.status_code != 401


def test_edit_autotrade_settings_requires_auth(client: TestClient):
    """Test that PUT /autotrade-settings/bots requires authentication."""
    response = client.put("/autotrade-settings/bots", json={"base_order_size": 15})
    assert response.status_code == 401


def test_get_paper_autotrade_settings_requires_auth(client: TestClient):
    """Test that GET /autotrade-settings/paper-trading requires authentication."""
    response = client.get("/autotrade-settings/paper-trading")
    assert response.status_code == 401


def test_edit_paper_autotrade_settings_requires_auth(client: TestClient):
    """Test that PUT /autotrade-settings/paper-trading requires authentication."""
    response = client.put(
        "/autotrade-settings/paper-trading", json={"base_order_size": 15}
    )
    assert response.status_code == 401


# Charts endpoints
def test_get_top_gainers_requires_auth(client: TestClient):
    """Test that GET /charts/top-gainers requires authentication."""
    response = client.get("/charts/top-gainers")
    assert response.status_code == 401


def test_get_top_losers_requires_auth(client: TestClient):
    """Test that GET /charts/top-losers requires authentication."""
    response = client.get("/charts/top-losers")
    assert response.status_code == 401


def test_get_btc_correlation_requires_auth(client: TestClient):
    """Test that GET /charts/btc-correlation requires authentication."""
    response = client.get("/charts/btc-correlation?symbol=ETHUSDT")
    assert response.status_code == 401


def test_get_adr_series_requires_auth(client: TestClient):
    """Test that GET /charts/adr-series requires authentication."""
    response = client.get("/charts/adr-series")
    assert response.status_code == 401


def test_get_algorithm_performance_requires_auth(client: TestClient):
    """Test that GET /charts/algorithm-performance requires authentication."""
    response = client.get("/charts/algorithm-performance")
    assert response.status_code == 401


# Asset index endpoints
def test_get_asset_indices_requires_auth(client: TestClient):
    """Test that GET /asset-index/ requires authentication."""
    response = client.get("/asset-index/")
    assert response.status_code == 401


def test_get_asset_index_requires_auth(client: TestClient):
    """Test that GET /asset-index/{index_id} requires authentication."""
    response = client.get("/asset-index/some-id")
    assert response.status_code == 401


def test_add_asset_index_requires_auth(client: TestClient):
    """Test that POST /asset-index/ requires authentication."""
    response = client.post("/asset-index/", params={"id": "test", "name": "Test"})
    assert response.status_code == 401


def test_edit_asset_index_requires_auth(client: TestClient):
    """Test that PUT /asset-index/{index_id} requires authentication."""
    response = client.put("/asset-index/some-id", params={"name": "Updated"})
    assert response.status_code == 401


def test_delete_asset_index_requires_auth(client: TestClient):
    """Test that DELETE /asset-index/{index_id} requires authentication."""
    response = client.delete("/asset-index/some-id")
    assert response.status_code == 401


# Test invalid token scenarios
def test_invalid_token_format(client: TestClient):
    """Test that endpoints reject malformed tokens."""
    headers = {"Authorization": "Bearer invalid-token-format"}
    response = client.get("/bot", headers=headers)
    assert response.status_code == 401


def test_missing_bearer_prefix(client: TestClient, valid_token: str):
    """Test that endpoints reject tokens without Bearer prefix."""
    headers = {"Authorization": valid_token}
    response = client.get("/bot", headers=headers)
    assert response.status_code == 401


def test_empty_token(client: TestClient):
    """Test that endpoints reject empty tokens."""
    headers = {"Authorization": "Bearer "}
    response = client.get("/bot", headers=headers)
    assert response.status_code == 401


# Test that login endpoint does NOT require authentication
def test_login_does_not_require_auth(client: TestClient):
    """Test that POST /user/login does not require authentication."""
    response = client.post(
        "/user/login",
        data={"username": "test@example.com", "password": "testpassword"},
    )
    # Should not return 401 - will return 400 or other error for invalid credentials
    assert response.status_code != 401


# Test that root endpoint does NOT require authentication
def test_root_does_not_require_auth(client: TestClient):
    """Test that GET / does not require authentication."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "online"}
