from fastapi.testclient import TestClient
from typing import Generator
from unittest.mock import MagicMock

from pybinbot import UserRoles
from pytest import fixture
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from databases.utils import get_session
from databases.tables.autotrade_table import AutotradeTable
from main import app

mocked_db_data = AutotradeTable(
    id="autotrade_settings",
    base_order_size=15.0,
    test_autotrade=False,
    trailing_deviation=0.63,
    stop_loss=0.0,
    fiat="USDC",
    telegram_signals=True,
    close_condition="dynamic_trailing",
    autotrade=True,
    candlestick_interval="15m",
    updated_at=1732388868477.8518,
    trailing=True,
    trailing_profit=2.3,
    take_profit=2.3,
    max_request=500,
    max_active_autotrade_bots=1,
)


def override_get_current_user():
    return UserTokenData(
        email="test@example.com", role=UserRoles.admin, expires_in=1732388868477
    )


@fixture()
def client() -> Generator[TestClient, None, None]:
    session_mock = MagicMock()
    session_mock.exec.return_value.first.return_value = mocked_db_data
    session_mock.get.return_value = mocked_db_data
    session_mock.add.return_value = MagicMock(return_value=None)
    session_mock.commit.return_value = MagicMock(return_value=None)
    # Store the original override
    original_override = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_current_user] = override_get_current_user
    # Set the mock for this test
    app.dependency_overrides[get_session] = lambda: session_mock
    client = TestClient(app)
    yield client
    # Restore the original override (the conftest one)
    if original_override is not None:
        app.dependency_overrides[get_session] = original_override
    else:
        app.dependency_overrides.pop(get_session, None)


def test_get_autotrade_settings(client: TestClient) -> None:
    r = client.get("/autotrade-settings/bots")
    assert r.status_code == 200
    result = r.json()
    assert result["data"] == mocked_db_data.model_dump()


def test_edit_autotrade_settings(client: TestClient) -> None:
    r = client.put(
        "/autotrade-settings/bots",
        json={
            "base_order_size": 15.0,
            "test_autotrade": False,
            "trailing_deviation": 0.63,
            "stop_loss": 0.0,
            "fiat": "USDC",
            "telegram_signals": True,
            "close_condition": "dynamic_trailing",
            "autotrade": True,
            "candlestick_interval": "15m",
            "trailing": True,
            "trailing_profit": 2.3,
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
