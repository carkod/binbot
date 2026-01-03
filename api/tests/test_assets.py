from fastapi.testclient import TestClient
from pytest import mark

from main import app

app_client = TestClient(app)


@mark.vcr("cassettes/test_get_raw_balance.yaml")
def test_get_raw_balance():
    response = app_client.get("/account/balance/raw")
    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert isinstance(content["data"], list)
    assert all("asset" in x for x in content["data"])


@mark.vcr("cassettes/test_store_balance.yaml")
def test_store_balance():
    response = app_client.get("/account/store-balance")
    assert response.status_code == 200
    content = response.json()
    assert "message" in content
