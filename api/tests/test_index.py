from app import create_app
from fastapi.testclient import TestClient

app = create_app()
client = TestClient(app)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Online"}
