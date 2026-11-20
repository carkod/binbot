from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.user.services.auth import get_current_user


@pytest.mark.parametrize("path", ["/symbol/store", "/symbol/reingest"])
def test_symbol_ingestion_routes_run_background_ingestion(client, monkeypatch, path):
    etl = Mock()
    monkeypatch.setattr("api.symbols.routes.SymbolDataEtl", Mock(return_value=etl))

    response = client.get(path, params={"delete_existing": True})

    assert response.status_code == 200
    assert response.json()["error"] == 0
    etl.etl_symbols_ingestion.assert_called_once_with(True)


def test_delete_symbol_requires_authentication():
    with patch.dict(app.dependency_overrides):
        app.dependency_overrides.pop(get_current_user, None)
        response = TestClient(app).delete("/symbol/BTCUSDT")

    assert response.status_code == 401
