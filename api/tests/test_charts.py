from fastapi.testclient import TestClient

from exchange_apis.coingecko import CoinGecko
from main import app

client = TestClient(app)


def _mock_kucoin_futures_tickers():
    return [
        {
            "symbol": "BTCUSDTM",
            "base": "BTC",
            "target": "USDT",
            "contract_type": "perpetual",
            "last": 65000.0,
            "h24_percentage_change": 12.0,
            "open_interest_usd": 5000000.0,
            "h24_volume": 9000000.0,
            "funding_rate": 0.02,
            "last_traded": 1710000000,
            "expired_at": None,
        },
        {
            "symbol": "SOLUSDTM",
            "base": "SOL",
            "target": "USDT",
            "contract_type": "perpetual",
            "last": 150.0,
            "h24_percentage_change": -5.0,
            "open_interest_usd": 700000.0,
            "h24_volume": 600000.0,
            "funding_rate": -0.01,
            "last_traded": 1710000000,
            "expired_at": None,
        },
    ]


def test_top_gainers(monkeypatch):
    monkeypatch.setattr(
        CoinGecko,
        "get_kucoin_futures_tickers",
        lambda _self: _mock_kucoin_futures_tickers(),
    )

    response = client.get("/charts/top-gainers")

    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["symbol"] == "BTCUSDTM"
    assert data["data"][0]["h24_percentage_change"] == 12.0


def test_top_losers(monkeypatch):
    monkeypatch.setattr(
        CoinGecko,
        "get_kucoin_futures_tickers",
        lambda _self: _mock_kucoin_futures_tickers(),
    )

    response = client.get("/charts/top-losers")

    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["symbol"] == "SOLUSDTM"
    assert data["data"][0]["h24_percentage_change"] == -5.0
