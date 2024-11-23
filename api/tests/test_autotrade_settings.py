from fastapi.testclient import TestClient


def test_get_autotrade_settings(client: TestClient) -> None:
    r = client.get(
        "/autotrade-settings/bots",
    )
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
        "message": 'Successfully updated settings',
    }
