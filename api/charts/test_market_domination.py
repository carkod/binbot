import pytest
from fastapi.testclient import TestClient
from mongomock import Database, MongoClient
from api.charts.controllers import MarketDominationController
from main import app

client: MongoClient = MongoClient()
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

    monkeypatch.setattr(Database, "_db", new_init)
    monkeypatch.setattr(MarketDominationController, "get_market_domination", lambda a, size, *arg: data)


def test_get_market_domination(patch_database):

    response = app_client.get("/charts/market-domination")

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
