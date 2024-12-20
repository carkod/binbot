from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from pytest import fixture
from database.utils import get_session
from tests.conftest import MockAsyncBaseProducer
from database.models.autotrade_table import AutotradeTable
from main import app


@fixture()
def client() -> TestClient:
    session_mock = MagicMock()
    mocked_db_data = AutotradeTable(
        id="autotrade_settings",
        base_order_size=15.0,
        test_autotrade=False,
        trailling_deviation=0.63,
        stop_loss=0.0,
        balance_to_use="USDC",
        telegram_signals=True,
        close_condition="dynamic_trailling",
        autotrade=True,
        candlestick_interval="15m",
        updated_at=1732388868477.8518,
        trailling=True,
        trailling_profit=2.3,
        take_profit=2.3,
        max_request=500,
        max_active_autotrade_bots=1,
    )
    session_mock.exec.return_value.first.return_value = mocked_db_data
    session_mock.get.return_value = mocked_db_data
    session_mock.add.return_value = MagicMock(return_value=None)
    session_mock.commit.return_value = MagicMock(return_value=None)
    app.dependency_overrides[get_session] = lambda: session_mock
    client = TestClient(app)
    return client


def test_get_autotrade_settings(client) -> None:
    r = client.get("/autotrade-settings/bots")
    assert r.status_code == 200
    result = r.json()
    assert result == {
        "message": "Successfully retrieved settings",
        "data": {
            "id": "autotrade_settings",
            "base_order_size": 15.0,
            "test_autotrade": False,
            "trailling_deviation": 0.63,
            "stop_loss": 0.0,
            "fiat": "USDC",
            # Below to be deprecated
            "balance_to_use": "USDC",
            "telegram_signals": True,
            "close_condition": "dynamic_trailling",
            "autotrade": True,
            "candlestick_interval": "15m",
            "updated_at": 1732388868477.8518,
            "trailling": True,
            "trailling_profit": 2.3,
            "take_profit": 2.3,
            "max_request": 500,
            "max_active_autotrade_bots": 1,
        },
    }


@patch("autotrade.controller.AsyncBaseProducer", MockAsyncBaseProducer)
def test_edit_autotrade_settings(client: TestClient) -> None:
    r = client.put(
        "/autotrade-settings/bots",
        json={
            "base_order_size": 15.0,
            "test_autotrade": False,
            "trailling_deviation": 0.63,
            "stop_loss": 0.0,
            "balance_to_use": "USDC",
            "telegram_signals": True,
            "close_condition": "dynamic_trailling",
            "autotrade": True,
            "candlestick_interval": "15m",
            "trailling": True,
            "trailling_profit": 2.3,
            "take_profit": 2.3,
            "max_request": 500,
            "max_active_autotrade_bots": 1,
        },
    )
    assert r.status_code == 200
    result = r.json()
    assert result == {
        "message": "Successfully updated settings",
    }
