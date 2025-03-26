from fastapi.testclient import TestClient
from main import app
from pytest import fixture, mark


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


mock_id = "b687d14a-747e-4b76-b89b-cd05aaf6aa46"
mock_symbol = "TRXUSDC"
response_payload = {
    "message": "Successfully found one paper trading bot.",
    "error": 0,
    "data": {
        "pair": "TRXUSDC",
        "fiat": "USDC",
        "base_order_size": 2.0,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 0,
        "created_at": 1743217480091.0,
        "updated_at": 1743217480091.0,
        "dynamic_trailling": True,
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "status": "inactive",
        "stop_loss": 3.0,
        "margin_short_reversal": True,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 2.8,
        "trailling_profit": 2.3,
        "strategy": "long",
        "id": "b687d14a-747e-4b76-b89b-cd05aaf6aa46",
        "orders": [],
        "deal": {
            "current_price": 0.0,
            "take_profit_price": 0.0,
            "trailling_stop_loss_price": 0.0,
            "trailling_profit_price": 0.0,
            "stop_loss_price": 0.0,
            "total_interests": 0.0,
            "total_commissions": 0.0,
            "margin_loan_id": 0,
            "margin_repay_id": 0,
            "opening_price": 0.0,
            "opening_qty": 0.0,
            "opening_timestamp": 0,
            "closing_price": 0.0,
            "closing_qty": 0.0,
            "closing_timestamp": 0,
        },
    },
}


@mark.vcr("cassettes/test_paper_trading_get_one.yaml")
def test_paper_trading_get_one(client: TestClient):
    response = client.get(f"/paper-trading/{mock_id}")

    assert response.status_code == 200
    content = response.json()
    assert content == response_payload


@mark.vcr("cassettes/test_paper_trading_get_one_by_symbol.yaml")
def test_paper_trading_get_one_by_symbol(client: TestClient):
    response = client.get("/paper-trading/symbol/ADXUSDC")

    assert response.status_code == 200
    content = response.json()
    assert content == {
        "message": "Successfully found one bot.",
        "error": 0,
        "data": {
            "pair": "ADXUSDC",
            "fiat": "USDC",
            "base_order_size": 15.0,
            "candlestick_interval": "15m",
            "close_condition": "dynamic_trailling",
            "cooldown": 360,
            "created_at": 1733973560249.0,
            "updated_at": 1733973560249.0,
            "dynamic_trailling": False,
            "logs": [],
            "mode": "manual",
            "name": "Default bot",
            "status": "inactive",
            "stop_loss": 3.0,
            "margin_short_reversal": False,
            "take_profit": 2.3,
            "trailling": True,
            "trailling_deviation": 3.0,
            "trailling_profit": 0.0,
            "strategy": "long",
            "id": "87c18ab2-5575-4330-aa14-95d3fbbe99d7",
            "orders": [],
            "deal": {
                "current_price": 0.0,
                "take_profit_price": 0.0,
                "trailling_stop_loss_price": 0.0,
                "trailling_profit_price": 0.0,
                "stop_loss_price": 0.0,
                "total_interests": 0.0,
                "total_commissions": 0.0,
                "margin_loan_id": 0,
                "margin_repay_id": 0,
                "opening_price": 0.0,
                "opening_qty": 0.0,
                "opening_timestamp": 0,
                "closing_price": 0.0,
                "closing_qty": 0.0,
                "closing_timestamp": 0,
            },
        },
    }


@mark.vcr("cassettes/test_paper_trading_get_bots.yaml")
def test_paper_trading_get_bots(client: TestClient):
    response = client.get("/paper-trading")

    assert response.status_code == 200
    content = response.json()
    # Avoid testing internal objects
    # timestamps are generated
    assert content["data"][0] == {
        "close_condition": "dynamic_trailling",
        "updated_at": 1733973560249.0,
        "mode": "manual",
        "trailling_deviation": 3.0,
        "dynamic_trailling": False,
        "trailling_profit": 0.0,
        "cooldown": 360,
        "logs": [],
        "strategy": "long",
        "id": "86da4c65-2728-4625-be61-a1d5f44d706f",
        "fiat": "USDC",
        "name": "Default bot",
        "pair": "ADXUSDC",
        "status": "inactive",
        "base_order_size": 15.0,
        "stop_loss": 3.0,
        "margin_short_reversal": False,
        "candlestick_interval": "15m",
        "take_profit": 2.3,
        "created_at": 1733973560249.0,
        "trailling": True,
    }


@mark.vcr("cassettes/test_paper_trading_create_bot.yaml")
def test_paper_trading_create_bot(client: TestClient):
    payload = {
        "status": "inactive",
        "balance_available": 0,
        "base_order_size": 2,
        "fiat": "USDC",
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "pair": "TRXUSDC",
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 2.8,
        "trailling_profit": 2.3,
        "dynamic_trailling": True,
        "stop_loss": 3,
        "margin_short_reversal": True,
        "strategy": "long",
    }

    response = client.post("/paper-trading", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == {
        "pair": "TRXUSDC",
        "fiat": "USDC",
        "base_order_size": 2.0,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 0,
        "created_at": 1743217480091.0,
        "updated_at": 1743217480091.0,
        "dynamic_trailling": True,
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "status": "inactive",
        "stop_loss": 3.0,
        "margin_short_reversal": True,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 2.8,
        "trailling_profit": 2.3,
        "strategy": "long",
        "id": "b687d14a-747e-4b76-b89b-cd05aaf6aa46",
        "deal": {
            "current_price": 0.0,
            "take_profit_price": 0.0,
            "trailling_stop_loss_price": 0.0,
            "trailling_profit_price": 0.0,
            "stop_loss_price": 0.0,
            "total_interests": 0.0,
            "total_commissions": 0.0,
            "margin_loan_id": 0,
            "margin_repay_id": 0,
            "opening_price": 0.0,
            "opening_qty": 0.0,
            "opening_timestamp": 0,
            "closing_price": 0.0,
            "closing_qty": 0.0,
            "closing_timestamp": 0,
        },
        "orders": [],
    }


@mark.vcr("cassettes/test_paper_trading_edit_bot.yaml")
def test_paper_trading_edit_bot(client: TestClient):
    payload = {
        "pair": "TRXUSDC",
        "fiat": "USDC",
        "base_order_size": 50,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 0,
        "created_at": 1743217942076,
        "updated_at": 1743217942076,
        "dynamic_trailling": True,
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "status": "inactive",
        "stop_loss": 3,
        "margin_short_reversal": True,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 2.8,
        "trailling_profit": 2.3,
        "strategy": "long",
        "id": "2d1966f6-0924-45ab-ae47-2b8c20408e22",
    }

    response = client.put(
        "/paper-trading/2d1966f6-0924-45ab-ae47-2b8c20408e22", json=payload
    )

    assert response.status_code == 200
    content = response.json()
    assert content == {
        "message": "Bot updated",
        "error": 0,
        "data": {
            "pair": "TRXUSDC",
            "fiat": "USDC",
            "base_order_size": 50,
            "candlestick_interval": "15m",
            "close_condition": "dynamic_trailling",
            "cooldown": 0,
            "created_at": 1743217942076,
            "updated_at": 1743217942076,
            "dynamic_trailling": True,
            "logs": [],
            "mode": "manual",
            "name": "terminal_1743217337463",
            "status": "inactive",
            "stop_loss": 3,
            "margin_short_reversal": True,
            "take_profit": 2.3,
            "trailling": True,
            "trailling_deviation": 2.8,
            "trailling_profit": 2.3,
            "strategy": "long",
            "id": "2d1966f6-0924-45ab-ae47-2b8c20408e22",
            "deal": {
                "current_price": 0,
                "take_profit_price": 0,
                "trailling_stop_loss_price": 0,
                "trailling_profit_price": 0,
                "stop_loss_price": 0,
                "total_interests": 0,
                "total_commissions": 0,
                "margin_loan_id": 0,
                "margin_repay_id": 0,
                "opening_price": 0,
                "opening_qty": 0,
                "opening_timestamp": 0,
                "closing_price": 0,
                "closing_qty": 0,
                "closing_timestamp": 0,
            },
            "orders": [],
        },
    }


@mark.vcr("cassettes/test_paper_trading_delete_bot.yaml")
def test_paper_trading_delete_bot():
    # Fix missing json arg for delete tests
    class CustomTestClient(TestClient):
        def delete_with_payload(self, **kwargs):
            return self.request(method="DELETE", **kwargs)

    client = CustomTestClient(app)
    response = client.delete_with_payload(
        url="/paper-trading", json=["f801881f-93e7-4da2-9258-290c74e31219"]
    )

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Successfully deleted bot!"


@mark.vcr("cassettes/test_paper_trading_activate_by_id.yaml")
def test_paper_trading_activate_by_id(client: TestClient):
    response = client.get(f"/paper-trading/activate/{mock_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"] == {
        "pair": "TRXUSDC",
        "fiat": "USDC",
        "base_order_size": 2.0,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 0,
        "created_at": 1743217480091.0,
        "updated_at": 1743217480091.0,
        "dynamic_trailling": True,
        "logs": [],
        "mode": "manual",
        "name": "terminal_1743217337463",
        "status": "active",
        "stop_loss": 3.0,
        "margin_short_reversal": True,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 2.8,
        "trailling_profit": 2.3,
        "strategy": "long",
        "id": "b687d14a-747e-4b76-b89b-cd05aaf6aa46",
        "deal": {
            "current_price": 0.2345,
            "take_profit_price": 0.2575,
            "trailling_stop_loss_price": 0.0,
            "trailling_profit_price": 0.2398,
            "stop_loss_price": 0.2274,
            "total_interests": 0.0,
            "total_commissions": 0.0,
            "margin_loan_id": 0,
            "margin_repay_id": 0,
            "opening_price": 0.2345,
            "opening_qty": 1.0,
            "opening_timestamp": 1743274909753,
            "closing_price": 0.0,
            "closing_qty": 0.0,
            "closing_timestamp": 0,
        },
        "orders": [
            {
                "order_type": "LIMIT",
                "time_in_force": "GTC",
                "timestamp": 1743274909753,
                "order_id": 21686176,
                "order_side": "BUY",
                "pair": "TRXUSDC",
                "qty": 1.0,
                "status": "FILLED",
                "price": 0.2345,
                "deal_type": "base_order",
            }
        ],
    }


@mark.vcr("cassettes/test_paper_trading_deactivate.yaml")
def test_paper_trading_deactivate(client: TestClient):
    deactivate_id = "3c3dd13e-4233-4e91-b27b-97459ff33fe7"
    response = client.delete(f"/paper-trading/deactivate/{deactivate_id}")

    assert response.status_code == 200
    content = response.json()
    assert content == {
        "message": "Successfully triggered panic sell! Bot deactivated.",
        "data": {
            "pair": "TRXUSDC",
            "fiat": "USDC",
            "base_order_size": 2.0,
            "candlestick_interval": "15m",
            "close_condition": "dynamic_trailling",
            "cooldown": 0,
            "created_at": 1743217392564.0,
            "updated_at": 1743217392564.0,
            "dynamic_trailling": True,
            "logs": [
                "No balance found. Skipping panic sell",
                "Panic sell triggered. All active orders closed",
            ],
            "mode": "manual",
            "name": "terminal_1743217337463",
            "status": "completed",
            "stop_loss": 3.0,
            "margin_short_reversal": True,
            "take_profit": 2.3,
            "trailling": True,
            "trailling_deviation": 2.8,
            "trailling_profit": 2.3,
            "strategy": "long",
            "id": "3c3dd13e-4233-4e91-b27b-97459ff33fe7",
            "deal": {
                "current_price": 0.0,
                "take_profit_price": 0.0,
                "trailling_stop_loss_price": 0.0,
                "trailling_profit_price": 0.0,
                "stop_loss_price": 0.0,
                "total_interests": 0.0,
                "total_commissions": 0.0,
                "margin_loan_id": 0,
                "margin_repay_id": 0,
                "opening_price": 0.0,
                "opening_qty": 0.0,
                "opening_timestamp": 0,
                "closing_price": 0.2331,
                "closing_qty": 1.0,
                "closing_timestamp": 1743278459398,
            },
            "orders": [
                {
                    "order_type": "LIMIT",
                    "time_in_force": "GTC",
                    "timestamp": 1743278459398,
                    "order_id": 16429450,
                    "order_side": "SELL",
                    "pair": "TRXUSDC",
                    "qty": 1.0,
                    "status": "FILLED",
                    "price": 0.2331,
                    "deal_type": "take_profit",
                }
            ],
        },
    }
