from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_index():
    """
    Test status: online endpoint
    this is a test endpoint
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Online"}

def test_docs():
    """
    Test API docs
    """
    response = client.get("/docs")
    assert response.status_code == 200
