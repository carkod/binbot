from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from database.utils import get_session
from main import app
from pytest import fixture

# from tests.table_mocks import mocked_db_data
from fastapi.encoders import jsonable_encoder
from database.api_db import ApiDb
from database.models.deal_table import DealTable
from database.models.order_table import ExchangeOrderTable
from database.models.bot_table import BotTable
from tools.enum_definitions import DealType, Status, Strategy

base_order = ExchangeOrderTable(
    order_id=123,
    order_type="market",
    time_in_force="GTC",
    timestamp=0,
    order_side="buy",
    pair="BTCUSDC",
    qty=0.000123,
    status="filled",
    price=1.222,
    deal_type=DealType.base_order,
    total_commission=0,
)
take_profit_order = ExchangeOrderTable(
    order_id=456,
    order_type="limit",
    time_in_force="GTC",
    timestamp=0,
    order_side="sell",
    pair="BTCUSDC",
    qty=0.000123,
    status="filled",
    price=1.222,
    deal_type=DealType.take_profit,
    total_commission=0,
)
deal = DealTable(
    opening_price=1.7777,
    opening_qty=12,
    opening_timestamp=0,
    current_price=0,
    sd=0,
    avg_opening_price=0,
    take_profit_price=0.02333,
    trailling_stop_loss_price=0,
    trailling_profit_price=0,
    stop_loss_price=0,
    margin_loan_id=0,
    margin_repay_id=0,
    closing_timestamp=0,
    closing_price=0,
    closing_qty=0,
)
bot = BotTable(
    pair="BTCUSDC",
    balance_size_to_use="1",
    fiat="USDC",
    base_order_size=15,
    deal=deal,
    cooldown=0,
    logs=["Bot created"],
    mode="manual",
    name="Dummy bot",
    orders=[base_order, take_profit_order],
    status=Status.inactive,
    stop_loss=0,
    take_profit=2.3,
    trailling=True,
    trailling_deviation=0.63,
    trailling_profit=2.3,
    strategy=Strategy.long,
    short_opening_price=0,
    short_sell_price=0,
    total_commission=0,
)


@fixture()
def client() -> TestClient:
    client = TestClient(app)
    return client


def test_get_bots(client: TestClient):
    response = client.get("/bot")

    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) > 0
    assert content["data"][0] == jsonable_encoder(bot.model_dump())


# def test_get_one_by_id(client: TestClient):
#     response = client.get(f"/bot/{id}")

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == jsonable_encoder(mock_model_data.model_dump())


# def test_get_one_by_symbol(client: TestClient):
#     symbol = "ADXUSDC"
#     response = client.get(f"/bot/symbol/{symbol}")

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == jsonable_encoder(mock_model_data.model_dump())


# def test_create_bot(client: TestClient):
#     payload = {
#         "pair": "ADXUSDC",
#         "fiat": "USDC",
#         "base_order_size": 15,
#         "candlestick_interval": "15m",
#         "close_condition": "dynamic_trailling",
#         "cooldown": 360,
#         "created_at": 1733973560249.0,
#         "updated_at": 1733973560249.0,
#         "dynamic_trailling": False,
#         "logs": [],
#         "mode": "manual",
#         "name": "Default bot",
#         "status": "inactive",
#         "stop_loss": 3.0,
#         "margin_short_reversal": False,
#         "take_profit": 2.3,
#         "trailling": True,
#         "trailling_deviation": 3.0,
#         "trailling_profit": 0.0,
#         "strategy": "long",
#         "total_commission": 0.0,
#     }

#     response = client.post("/bot", json=payload)

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == mock_model_data_without_orders.model_dump()


# def test_edit_bot(client: TestClient):
#     payload = {
#         "pair": "ADXUSDC",
#         "fiat": "USDC",
#         "base_order_size": 15,
#         "candlestick_interval": "15m",
#         "close_condition": "dynamic_trailling",
#         "cooldown": 360,
#         "created_at": 1733973560249.0,
#         "updated_at": 1733973560249.0,
#         "dynamic_trailling": False,
#         "logs": [],
#         "mode": "manual",
#         "name": "coinrule_fast_and_slow_macd_2024-04-20T22:28",
#         "status": "inactive",
#         "stop_loss": 3.0,
#         "margin_short_reversal": False,
#         "take_profit": 2.3,
#         "trailling": True,
#         "trailling_deviation": 3.0,
#         "trailling_profit": 0.0,
#         "strategy": "long",
#         "total_commission": 0.0,
#     }

#     response = client.put(f"/bot/{id}", json=payload)

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == jsonable_encoder(mock_model_data.model_dump())


# def test_delete_bot():
#     # Fix missing json arg for delete tests
#     class CustomTestClient(TestClient):
#         def delete_with_payload(self, **kwargs):
#             return self.request(method="DELETE", **kwargs)

#     client = CustomTestClient(app)
#     payload = [id]
#     response = client.delete_with_payload(url="/bot", json=payload)

#     assert response.status_code == 200
#     content = response.json()
#     assert content["message"] == "Sucessfully deleted bot."


# @patch("bots.routes.SpotLongDeal", DealFactoryMock)
# def test_activate_by_id(client: TestClient):
#     response = client.get(f"/bot/activate/{id}")

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == mock_model_data.model_dump()


# @patch("bots.routes.SpotLongDeal", DealFactoryMock)
# def test_deactivate(client: TestClient):
#     response = client.delete(f"/bot/deactivate/{id}")

#     assert response.status_code == 200
#     content = response.json()
#     assert content["data"] == mock_model_data.model_dump()


# def test_post_bot_errors_str(client: TestClient):
#     """
#     Test submitting bot errors with a single string
#     """
#     payload = {"errors": "failed to create bot"}

#     response = client.post(f"/bot/errors/{id}", json=payload)

#     assert response.status_code == 200
#     content = response.json()
#     assert content["message"] == "Errors posted successfully."


# def test_post_bot_errors_list(client: TestClient):
#     """
#     Test submitting bot errors with a list of strings
#     """
#     payload = {"errors": ["failed to create bot", "failed to create deal"]}

#     response = client.post(f"/bot/errors/{id}", json=payload)

#     assert response.status_code == 200
#     content = response.json()
#     assert content["message"] == "Errors posted successfully."
