from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session
from charts.controllers import Candlestick
from database.models.autotrade_table import AutotradeTable

def test_get_autotrade_settings(
    client: TestClient, db: Session
) -> None:
    with (
        patch("app.utils.send_email", return_value=None),
    ):
        r = client.get(
            "/autotrade-settings",
        )
        assert 200 <= r.status_code < 300
        data = r.json()
        assert data
        assert data == {
            "balance_to_use": "USDC",
            "base_order_size": 15,
            "candlestick_interval": "fifteen_minutes",
            "max_active_autotrade_bots": 1,
            "stop_loss": 0,
            "take_profit": 2.3,
            "telegram_signals": True,
            "trailling": True,
            "trailling_deviation": 0.63,
            "trailling_profit": 2.3,
            "autotrade": True,
        }

