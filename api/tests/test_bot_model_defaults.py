from bots.models import BotModel, BotListResponse, BotPairsList
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

    first.orders.append("sentinel")

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
    first_pairs = BotPairsList()
    second_pairs = BotPairsList()
    first_pairs.data.append("BTCUSDC")
    assert second_pairs.data == []

    first_list = BotListResponse()
    second_list = BotListResponse()
    first_list.data.append("bot")
    assert second_list.data == []
