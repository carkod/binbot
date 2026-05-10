from fastapi.testclient import TestClient
from pytest import mark
from main import app

client = TestClient(app)


@mark.vcr("cassettes/test_top_losers.yaml")
def test_top_losers():
    response = client.get("/charts/top-losers")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
