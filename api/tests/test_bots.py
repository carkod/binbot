from fastapi.testclient import TestClient
from main import app
from pytest import fixture, mark


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


mock_id = "cff9e468-87ee-46fa-8678-17af132b8434"
mock_symbol = "ADXUSDC"


@mark.vcr("cassettes/test_get_one_by_id.yaml")
def test_get_one_by_id(client: TestClient):
    response = client.get(f"/bot/{mock_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "ADXUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["base_order_size"] == 15
    assert content["data"]["cooldown"] == 360


@mark.vcr("cassettes/test_get_one_by_symbol.yaml")
def test_get_one_by_symbol(client: TestClient):
    response = client.get(f"/bot/symbol/{mock_symbol}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "ADXUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["base_order_size"] == 15
    assert content["data"]["cooldown"] == 360


@mark.vcr("cassettes/test_get_bots.yaml")
def test_get_bots(client: TestClient):
    response = client.get("/bot")

    assert response.status_code == 200
    content = response.json()
    # Avoid testing internal objects
    # timestamps are generated
    assert content["data"][0]["pair"] == "ADXUSDC"
    assert content["data"][0]["fiat"] == "USDC"
    assert content["data"][0]["base_order_size"] == 15
    assert content["data"][0]["cooldown"] == 360


@mark.vcr("cassettes/test_create_bot.yaml")
def test_create_bot(client: TestClient):
    payload = {
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "base_order_size": 15,
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
        "total_commission": 0.0,
    }

    response = client.post("/bot", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "ADXUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["base_order_size"] == 15
    assert content["data"]["cooldown"] == 360


@mark.vcr("cassettes/test_edit_bot.yaml")
def test_edit_bot(client: TestClient):
    payload = {
        "pair": "ADXUSDC",
        "fiat": "USDC",
        "base_order_size": 15,
        "candlestick_interval": "15m",
        "close_condition": "dynamic_trailling",
        "cooldown": 360,
        "created_at": 1733973560249.0,
        "updated_at": 1733973560249.0,
        "dynamic_trailling": False,
        "logs": [],
        "mode": "manual",
        "name": "coinrule_fast_and_slow_macd_2024-04-20T22:28",
        "status": "inactive",
        "stop_loss": 3.0,
        "margin_short_reversal": False,
        "take_profit": 2.3,
        "trailling": True,
        "trailling_deviation": 3.0,
        "trailling_profit": 0.0,
        "strategy": "long",
        "total_commission": 0.0,
    }

    response = client.put(f"/bot/{mock_id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "ADXUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["base_order_size"] == 15
    assert content["data"]["cooldown"] == 360


@mark.vcr("cassettes/test_delete_bot.yaml")
def test_delete_bot():
    # Fix missing json arg for delete tests
    class CustomTestClient(TestClient):
        def delete_with_payload(self, **kwargs):
            return self.request(method="DELETE", **kwargs)

    client = CustomTestClient(app)
    delete_ids = [
        "7079023a-e3da-4049-8b31-7384dff94d1f",
        "260c4c9c-68bf-458f-9f00-bea4d1c57147",
    ]
    response = client.delete_with_payload(url="/bot", json=[delete_ids])

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Sucessfully deleted bot."


@mark.vcr("cassettes/test_activate_by_id.yaml")
def test_activate_by_id(client: TestClient):
    mock_activate_id = "44db75ee-15c2-4a48-a346-4ffdc3ac5506"
    response = client.get(f"/bot/activate/{mock_activate_id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "EPICUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["base_order_size"] == 20


@mark.vcr("cassettes/test_deactivate.yaml")
def test_deactivate(client: TestClient):
    response = client.delete(f"/bot/deactivate/{id}")

    assert response.status_code == 200
    content = response.json()
    assert content["data"]["pair"] == "ADXUSDC"
    assert content["data"]["fiat"] == "USDC"
    assert content["data"]["base_order_size"] == 15
    assert content["data"]["cooldown"] == 360


@mark.vcr("cassettes/test_post_bot_errors_str.yaml")
def test_post_bot_errors_str(client: TestClient):
    """
    Test submitting bot errors with a single string
    """
    payload = {"errors": "failed to create bot"}

    response = client.post(f"/bot/errors/{mock_id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."


@mark.vcr("cassettes/test_post_bot_errors_list.yaml")
def test_post_bot_errors_list(client: TestClient):
    """
    Test submitting bot errors with a list of strings
    """
    payload = {"errors": ["failed to create bot", "failed to create deal"]}

    response = client.post(f"/bot/errors/{mock_id}", json=payload)

    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Errors posted successfully."
