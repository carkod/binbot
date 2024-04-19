from urllib import response
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
import pytest
from account.assets import Assets
from db import Database, setup_db
from main import app
import mongomock


client = mongomock.MongoClient()
db = client.db

app_client = TestClient(app)


@pytest.fixture()
def patch_database(monkeypatch):
    data = [
        {
            "_id": "65d39b44a7ff2a5e843b1e0b",
            "time": "2024-02-19 18:17:40.479",
            "data": [
                {
                    "symbol": "PIXELUSDT",
                    "priceChangePercent": "15.000",
                    "volume": "1235816253.30000000",
                    "price": "0.64880000",
                }
            ],
        }
    ]

    def new_init(self):
        self._db = db

    monkeypatch.setattr(Assets, "_db", new_init)
    monkeypatch.setattr(Assets, "get_market_domination", lambda a, size, *arg: data)


@pytest.fixture()
def patch_raw_balances(monkeypatch):
    """
    Input data from API
    Confidential data has been removed
    """
    account_data = {
        "makerCommission": 10,
        "commissionRates": {
            "maker": "0.00100000",
        },
        "updateTime": 1713558823589,
        "accountType": "SPOT",
        "balances": [
            {"asset": "BTC", "free": 6.51e-06, "locked": 0.0},
            {"asset": "BNB", "free": 9.341e-05, "locked": 0.0},
            {"asset": "USDT", "free": 160.7613619, "locked": 0.0},
            {"asset": "NFT", "free": 31205.975795, "locked": 0.0},
        ],
        "permissions": ["LEVERAGED", "TRD_GRP_002", "TRD_GRP_009"],
    }

    monkeypatch.setattr(
        Assets, "get_account_balance", lambda a, asset=None: account_data
    )


def test_get_market_domination(monkeypatch, patch_database):

    response = app_client.get("/account/market-domination")

    # Assert the expected result
    expected_result = {
        "data": {
            "dates": ["2024-02-19 18:17:40.479"],
            "gainers_percent": [1235816253.3],
            "losers_percent": [0.0],
            "gainers_count": [1],
            "losers_count": [0],
            "total_volume": [801797585.14104],
        },
        "message": "Successfully retrieved market domination data.",
        "error": 0,
    }
    assert response.status_code == 200
    assert response.json() == expected_result


def test_get_raw_balance(patch_raw_balances):
    """
    Test get all raw_balances
    """

    response = app_client.get("/account/balance/raw")
    expected_result = [
        {"asset": "BTC", "free": 6.51e-06, "locked": 0.0},
        {"asset": "BNB", "free": 9.341e-05, "locked": 0.0},
        {"asset": "USDT", "free": 160.7613619, "locked": 0.0},
        {"asset": "NFT", "free": 31205.975795, "locked": 0.0},
    ]

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == expected_result
