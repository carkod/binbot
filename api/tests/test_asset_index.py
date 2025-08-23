from fastapi.testclient import TestClient
from pytest import mark
from main import app

client = TestClient(app)


# Fixtures for test data
def asset_index_payload():
    return {"id": "test-index", "name": "Test Index"}


@mark.vcr("cassettes/test_get_all.yaml")
def test_get_all_asset_indices():
    response = client.get("/asset-index/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@mark.vcr("cassettes/test_add_asset_index.yaml")
def test_add_asset_index():
    payload = asset_index_payload()
    response = client.post(
        "/asset-index/", params={"id": "new-index", "name": payload["name"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "new-index"
    assert data["name"] == payload["name"]


@mark.vcr("cassettes/test_get_asset_index.yaml")
def test_get_asset_index():
    payload = asset_index_payload()
    # Ensure the index exists
    client.post("/asset-index/", params=payload)
    response = client.get(f"/asset-index/{payload['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payload["id"]


@mark.vcr("cassettes/test_edit_asset_index.yaml")
def test_edit_asset_index():
    payload = asset_index_payload()
    response = client.put(f"/asset-index/{payload['id']}", params=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]


@mark.vcr("cassettes/test_delete_asset_index.yaml")
def test_delete_asset_index():
    payload = asset_index_payload()
    client.post("/asset-index/", params=payload)
    response = client.delete(f"/asset-index/{payload['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payload["id"]
    response = client.get(f"/asset-index/{payload['id']}")
    assert response.status_code == 404
