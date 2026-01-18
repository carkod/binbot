from fastapi.testclient import TestClient
from main import app

app_client = TestClient(app)


def test_store_balance():
    response = app_client.get("/account/store-balance")
    assert response.status_code == 200
    content = response.json()
    assert "message" in content
