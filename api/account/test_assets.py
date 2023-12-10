from unittest.mock import MagicMock
from account.assets import AccountAssets

def test_get_market_domination():
    # Mock the database and its find method
    db_mock = MagicMock()
    db_mock.market_domination.find.return_value = [
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

    # Create an instance of AccountAssets and set the mock database
    assets = AccountAssets()
    assets.db = db_mock

    # Call the get_market_domination method
    result = assets.get_market_domination(size=3)

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
