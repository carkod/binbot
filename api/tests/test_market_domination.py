from bson import ObjectId
import pytest
from fastapi.testclient import TestClient
from mongomock import MongoClient
from charts.controllers import MarketDominationController
from main import app
from datetime import datetime
from time import time
from typing import Optional
from pydantic import BaseModel
from tools.enum_definitions import BinanceKlineIntervals, Strategy


client: MongoClient = MongoClient()
db = client.db

app_client = TestClient(app)


class AutotradeSettingsMock(BaseModel):
    autotrade: bool = False
    updated_at: float = time() * 1000
    # Assuming 10 USDC is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
    base_order_size: float = 15
    candlestick_interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes
    # Deprecated, this is now up to binquant to set
    strategy: Optional[Strategy] = Strategy.long
    test_autotrade: bool = False
    trailling: bool = False
    trailling_deviation: float = 3
    trailling_profit: float = 2.4
    stop_loss: float = 0
    take_profit: float = 2.3
    fiat: str = "USDC"
    balance_size_to_use: float = 100
    max_request: int = 950
    system_logs: list[str] = []
    # Number of times update is requested
    telegram_signals: bool = True
    max_active_autotrade_bots: int = 1


@pytest.fixture()
def patch_database(monkeypatch):
    ticker_24 = [
        {
            "symbol": "ETHUSDC",
            "priceChange": "-0.00021000",
            "priceChangePercent": "-0.583",
            "weightedAvgPrice": "0.03587137",
            "prevClosePrice": "0.03602000",
            "lastPrice": "0.03580000",
            "lastQty": "0.03000000",
            "bidPrice": "0.03580000",
            "bidQty": "22.40370000",
            "askPrice": "0.03581000",
            "askQty": "48.84800000",
            "openPrice": "0.03601000",
            "highPrice": "0.03616000",
            "lowPrice": "0.03557000",
            "volume": "12802.80560000",
            "quoteVolume": "459.25423169",
            "openTime": 1730519705315,
            "closeTime": 1730606105315,
            "firstId": 471506510,
            "lastId": 471553341,
            "count": 46832,
        }
    ]
    data = [
        {
            "data": [
                {
                    "timestamp": datetime(2024, 11, 2, 23, 50, 48, 756000),
                    "symbol": "BNBUSDC",
                    "time": "2024-11-02 23:50:48.756",
                    "priceChangePercent": -0.803,
                    "price": 568.1,
                    "volume": 4784.27,
                    "_id": ObjectId("6726bafb949b62e284c28b39"),
                }
            ],
            "time": datetime(2024, 11, 2, 23, 50, 48, 756000),
        },
        {
            "data": [
                {
                    "timestamp": datetime(2024, 11, 2, 23, 50, 48, 756000),
                    "symbol": "BNBUSDC",
                    "time": "2024-11-02 23:50:48.756",
                    "priceChangePercent": -0.803,
                    "price": 568.1,
                    "volume": 4784.27,
                    "_id": ObjectId("6726bafb949b62e284c28b39"),
                }
            ],
            "time": datetime(2024, 11, 2, 23, 50, 48, 756000),
        },
        {
            "data": [
                {
                    "timestamp": datetime(2024, 11, 2, 23, 50, 48, 756000),
                    "symbol": "BNBUSDC",
                    "time": "2024-11-02 23:50:48.756",
                    "priceChangePercent": -0.803,
                    "price": 568.1,
                    "volume": 4784.27,
                    "_id": ObjectId("6726bafb949b62e284c28b39"),
                }
            ],
            "time": datetime(2024, 11, 2, 23, 50, 48, 756000),
        },
    ]

    def new_init(self):
        mongo_client: MongoClient = MongoClient()
        mongo_client.db.market_domination.insert_many(
            [
                {
                    "timestamp": datetime(2024, 11, 3, 3, 55, 5, 315000),
                    "time": "2024-11-03 03:55:05.315",
                    "symbol": "ETHUSDC",
                    "priceChangePercent": -0.583,
                    "price": 0.0358,
                    "volume": 12802.8056,
                }
            ]
        )
        self.collection = self.kafka_db.market_domination = mongo_client.db.collection
        self.autotrade_settings = AutotradeSettingsMock()

    monkeypatch.setattr(MarketDominationController, "__init__", new_init)
    # monkeypatch.setattr(MarketDominationController, "kafka_db.market_domination", lambda self: db)
    monkeypatch.setattr(MarketDominationController, "ticker_24", lambda self: ticker_24)

    monkeypatch.setattr(
        MarketDominationController, "get_market_domination", lambda a, size, *arg: data
    )
    return monkeypatch


def test_get_market_domination(patch_database):
    response = app_client.get("/charts/market-domination")

    # Assert the expected result
    expected_result = {
        "data": {
            "dates": [
                "2024-11-02 23:50:48.756000",
                "2024-11-02 23:50:48.756000",
                "2024-11-02 23:50:48.756000",
            ],
            "gainers_percent": [0.0, 0.0, 0.0],
            "losers_percent": [4784.27, 4784.27, 4784.27],
            "gainers_count": [0, 0, 0],
            "losers_count": [1, 1, 1],
            "total_volume": [
                2717943.7870000005,
                2717943.7870000005,
                2717943.7870000005,
            ],
        },
        "message": "Successfully retrieved market domination data.",
        "error": 0,
    }

    assert response.status_code == 200
    assert response.json() == expected_result


def test_store_market_domination(patch_database):
    response = app_client.get("/charts/store-market-domination")

    expected_result = {
        "message": "Successfully stored market domination data.",
        "error": 0,
    }
    assert response.status_code == 200
    assert response.json() == expected_result
