from account.assets import Assets
from main import app
from db import setup_db

import mongomock

test_client = mongomock.MongoClient()

async def get_test_client():
    return test_client

app.dependency_overrides[setup_db] = get_test_client

class TestAccount:

    def __init__(self) -> None:
        self.db = test_client["bots"]["market_domination"]
        pass

    def test_get_market_domination(self):
        # Mock the database and its find method
        data = [
            {
                "data": [
                    {"priceChangePercent": "0.5"},
                    {"priceChangePercent": "-0.3"},
                    {"priceChangePercent": "0.2"},
                    {"priceChangePercent": "-0.1"},
                ],
                "time": "2022-01-01",
            },
            {
                "data": [
                    {"priceChangePercent": "0.1"},
                    {"priceChangePercent": "-0.2"},
                    {"priceChangePercent": "0.3"},
                    {"priceChangePercent": "-0.4"},
                ],
                "time": "2022-01-02",
            },
            {
                "data": [
                    {"priceChangePercent": "0.4"},
                    {"priceChangePercent": "-0.5"},
                    {"priceChangePercent": "0.6"},
                    {"priceChangePercent": "-0.7"},
                ],
                "time": "2022-01-03",
            },
        ]

        self.db.insert_one(data)

        # Create an instance of AccountAssets and set the mock database
        assets = Assets()

        # Call the get_market_domination method
        result = assets.get_market_domination()

        # Assert the expected result
        expected_result = {
            "data": {
                "dates": ["2022-01-01", "2022-01-02", "2022-01-03"],
                "gainers_percent": [0.5, 0.1, 0.4],
                "losers_percent": [0.3, 0.2, 0.5],
                "gainers_count": 3,
                "losers_count": 3,
            },
            "message": "Successfully retrieved market domination data.",
            "error": 0,
        }
        assert result == expected_result
