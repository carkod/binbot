from app import create_app
from fastapi.testclient import TestClient

app = create_app()
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
