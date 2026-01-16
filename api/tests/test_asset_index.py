from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock
from databases.tables.asset_index_table import AssetIndexTable

client = TestClient(app)


# Fixtures for test data
def asset_index_payload():
    return {"id": "test-index", "name": "Test Index"}


def mock_asset_index():
    """Create a mock AssetIndexTable"""
    index = AssetIndexTable(id="test-index", name="Test Index")
    return index


@patch("asset_index.routes.AssetIndexCrud")
def test_add_asset_index(mock_crud_class):
    """Test adding an asset index"""
    mock_crud = MagicMock()
    mock_crud_class.return_value = mock_crud
    mock_crud.add_index.return_value = mock_asset_index()

    values = asset_index_payload()
    response = client.post("/asset-index/", params=values)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == values["id"]
    assert data["name"] == values["name"]


@patch("asset_index.routes.AssetIndexCrud")
def test_get_all_asset_indices(mock_crud_class):
    """Test getting all asset indices"""
    mock_crud = MagicMock()
    mock_crud_class.return_value = mock_crud
    mock_crud.get_all.return_value = [mock_asset_index()]

    response = client.get("/asset-index/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch("asset_index.routes.AssetIndexCrud")
def test_get_asset_index(mock_crud_class):
    """Test getting a single asset index"""
    mock_crud = MagicMock()
    mock_crud_class.return_value = mock_crud
    mock_crud.get_index.return_value = mock_asset_index()

    payload = asset_index_payload()
    response = client.get(f"/asset-index/{payload['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payload["id"]


@patch("asset_index.routes.AssetIndexCrud")
def test_edit_asset_index(mock_crud_class):
    """Test editing an asset index"""
    mock_crud = MagicMock()
    mock_crud_class.return_value = mock_crud
    mock_crud.edit_index.return_value = mock_asset_index()

    payload = asset_index_payload()
    response = client.put(f"/asset-index/{payload['id']}", params=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]


@patch("asset_index.routes.AssetIndexCrud")
def test_delete_asset_index(mock_crud_class):
    """Test deleting an asset index"""
    mock_crud = MagicMock()
    mock_crud_class.return_value = mock_crud
    mock_crud.delete_index.return_value = mock_asset_index()

    payload = asset_index_payload()
    response = client.delete(f"/asset-index/{payload['id']}")
    assert response.status_code == 200
