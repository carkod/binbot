from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_index():
    """
    Test status: online endpoint
    this is a test endpoint
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "online"}


def test_docs():
    """
    Test API docs
    """
    response = client.get("/docs")
    assert response.status_code == 200
