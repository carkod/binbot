from fastapi.testclient import TestClient
from pytest import mark

from main import app

client = TestClient(app)


@mark.vcr("cassettes/test_top_gainers.yaml")
def test_top_gainers():
    response = client.get("/charts/top-gainers")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


@mark.vcr("cassettes/test_top_losers.yaml")
def test_top_losers():
    response = client.get("/charts/top-losers")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


@mark.vcr("cassettes/test_get_btc_correlation.yaml")
def test_get_btc_correlation():
    symbol = "BTCUSDC"
    response = client.get(f"/charts/btc-correlation?symbol={symbol}")
    # Accept 200 or 404 depending on test DB state
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "data" in data or "corr" in data
