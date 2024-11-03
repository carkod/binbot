from fastapi.testclient import TestClient
import pytest
from research.controller import Controller
from main import app
from mongomock import MongoClient

@pytest.fixture()
def mock_research(monkeypatch):
    blacklist = [
        {
            "_id": "65d39b44a7ff2a5e843b1e0b",
            "time": "2024-02-19 18:17:40.479",
            "data": [
                {
                    "_id": "1INCHDOWNUSDT",
                    "pair": "1INCHDOWNUSDT",
                    "reason": "Fiat coin or Margin trading",
                }
            ],
        }
    ]

    def new_init(self):
        mongo_client: MongoClient = MongoClient()
        self._db = mongo_client.db

    monkeypatch.setattr(Controller, "_db", new_init)
    monkeypatch.setattr(Controller, "get_blacklist", lambda self: blacklist)


def test_get_blacklisted(mock_research):
    client = TestClient(app)
    response = client.get("/research/blacklist")

    # Assert the expected result
    expected_result = {
        "message": "Successfully retrieved blacklist",
        "data": [
            {
                "_id": "65d39b44a7ff2a5e843b1e0b",
                "time": "2024-02-19 18:17:40.479",
                "data": [
                    {
                        "_id": "1INCHDOWNUSDT",
                        "pair": "1INCHDOWNUSDT",
                        "reason": "Fiat coin or Margin trading",
                    }
                ],
            }
        ],
    }
    assert response.status_code == 200
    assert response.json() == expected_result
