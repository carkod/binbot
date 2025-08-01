from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from pytest import fixture
from account.assets import Assets
from main import app
from database.utils import get_session


MockAutotradeCrud = MagicMock()
MockAutotradeCrud.return_value.get_settings.return_value.fiat = "USDC"


session_mock = MagicMock()
session_mock.add.return_value = MagicMock(return_value=None)
session_mock.commit.return_value = MagicMock(return_value=None)
session_mock.refresh.return_value = MagicMock(return_value=None)
app.dependency_overrides[get_session] = lambda: session_mock
app_client = TestClient(app)


@fixture()
def patch_database(monkeypatch):
    itemized_balance = [
        {"asset": "BTC", "free": 6.51e-06, "locked": 0.0},
        {"asset": "BNB", "free": 9.341e-05, "locked": 0.0},
        {"asset": "USDC", "free": 5.2, "locked": 0.0},
        {"asset": "NFT", "free": 1, "locked": 0.0},
    ]

    monkeypatch.setattr(
        Assets, "get_raw_balance", lambda self, asset=None: itemized_balance
    )


@fixture()
def patch_raw_balances(monkeypatch):
    """
    Input data from API
    Confidential data has been removed
    """
    account_data = {
        "makerCommission": 10,
        "commissionRates": {
            "maker": "0.00100000",
            "taker": "0.00100000",
            "buyer": "0.00100000",
            "seller": "0.00100000",
        },
        "updateTime": 1713558823589,
        "accountType": "SPOT",
        "balances": [
            {"asset": "BTC", "free": 6.51e-06, "locked": 0.0},
            {"asset": "BNB", "free": 9.341e-05, "locked": 0.0},
            {"asset": "USDC", "free": 5.2, "locked": 0.0},
            {"asset": "NFT", "free": 1, "locked": 0.0},
        ],
        "permissions": ["LEVERAGED", "TRD_GRP_002", "TRD_GRP_009"],
        "uid": 123456789,
    }

    monkeypatch.setattr(
        Assets, "get_account_balance", lambda a, asset=None: account_data
    )


@fixture()
def patch_total_fiat(monkeypatch):
    """
    Input data from API
    Confidential data has been removed
    """
    account_data = [
        {"activate": True, "balance": "0.001", "walletName": "Spot"},
        {"activate": True, "balance": "0", "walletName": "Funding"},
        {"activate": True, "balance": "0", "walletName": "Cross Margin"},
        {"activate": True, "balance": "0", "walletName": "Isolated Margin"},
        {"activate": True, "balance": "0", "walletName": "USDⓈ-M Futures"},
        {"activate": True, "balance": "0", "walletName": "COIN-M Futures"},
        {"activate": True, "balance": "0", "walletName": "Earn"},
        {"activate": False, "balance": "0", "walletName": "Options"},
        {"activate": False, "balance": "0", "walletName": "Trading Bots"},
    ]

    monkeypatch.setattr(Assets, "get_wallet_balance", lambda self: account_data)
    monkeypatch.setattr(
        Assets, "get_ticker_price", lambda self, symbol: "98418.60000000"
    )


@fixture()
def patch_store_balance(monkeypatch):
    """
    Input data from API
    Confidential data has been removed
    """
    wallet_balance = [{"activate": True, "balance": "0.001", "walletName": "Spot"}]

    monkeypatch.setattr(Assets, "get_available_fiat", lambda self: 5.2)
    monkeypatch.setattr(Assets, "get_wallet_balance", lambda self: wallet_balance)
    monkeypatch.setattr(Assets, "get_ticker_price", lambda self, pair: "59095.79000000")
    monkeypatch.setattr(
        Assets,
        "map_balance_with_benchmark",
        lambda self, total_balance, total_estimated_fiat: None,
    )


@patch("account.assets.AutotradeCrud", MockAutotradeCrud)
def test_get_raw_balance(patch_database, patch_raw_balances):
    """
    Test get all raw_balances
    """
    response = app_client.get("/account/balance/raw")
    expected_result = [
        {"asset": "BTC", "free": 6.51e-06, "locked": 0.0},
        {"asset": "BNB", "free": 9.341e-05, "locked": 0.0},
        {"asset": "USDC", "free": 5.2, "locked": 0.0},
        {"asset": "NFT", "free": 1, "locked": 0.0},
    ]

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == expected_result


@patch("account.assets.AutotradeCrud", MockAutotradeCrud)
def test_total_fiat(patch_total_fiat):
    """
    Test get balance estimates
    """

    response = app_client.get("/account/fiat")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == 98.41860000000001


@patch("account.assets.AutotradeCrud", MockAutotradeCrud)
def test_available_fiat(patch_database, patch_raw_balances):
    """
    Test available fiat
    """

    response = app_client.get("/account/fiat/available")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == 5.2


@patch("account.assets.AutotradeCrud", MockAutotradeCrud)
def test_store_balance(patch_database, patch_store_balance):
    """
    Test store balance as an endpoint
    This runs as a cron job in production
    """

    response = app_client.get("/account/store-balance")

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Successfully stored balance."
