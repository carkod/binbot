from bots.models import BotModel, BotListResponse, BotPairsList, OrderModel
from pybinbot import OrderStatus
from databases.tables.bot_table import BotTable, PaperTradingTable


def test_bot_model_orders_are_isolated():
    first = BotModel(
        pair="BTCUSDC",
        logs=[],
    )
    second = BotModel(
        pair="ETHUSDC",
        logs=[],
    )

    first.orders.append(
        OrderModel(
            deal_type=DealType.base_order,
            order_id="test-order-id",
            order_side="buy",
            order_type="MARKET",
            pair="BTCUSDC",
            price=1.0,
            qty=1.0,
            status=OrderStatus.FILLED,
            time_in_force="GTC",
            timestamp=0,
        )
    )

    assert second.orders == []


def test_bot_table_logs_are_isolated():
    first = BotTable(pair="BTCUSDC")
    second = BotTable(pair="ETHUSDC")

    first.logs.append("first")

    assert second.logs == []


def test_paper_trading_logs_are_isolated():
    first = PaperTradingTable(pair="BTCUSDC")
    second = PaperTradingTable(pair="ETHUSDC")

    first.logs.append("first")

    assert second.logs == []


def test_response_lists_are_isolated():
    first_pairs = BotPairsList(message="")
    second_pairs = BotPairsList(message="")
    first_pairs.data.append("BTCUSDC")
    assert second_pairs.data == []

    first_list = BotListResponse(message="")
    second_list = BotListResponse(message="")
    first_list.data.append("bot")
    assert second_list.data == []
