from api.databases.tables.bot_table import BotTable
from api.databases.tables.deal_table import DealTable
from api.databases.tables.order_table import ExchangeOrderTable
from pybinbot import (
    BinanceKlineIntervals,
    CloseConditions,
    DealType,
    OrderStatus,
    OrderType,
    Position,
    Status,
)
from uuid import UUID

ts = 1733973560249.0
id = "02031768-fbb9-4cc7-b549-642f15ab787b"

orders = [
    ExchangeOrderTable(
        id=UUID(id),
        order_id="123",
        order_type=OrderType.market,
        time_in_force="GTC",
        timestamp=0,
        order_side="buy",
        pair="BTCUSDC",
        qty=0.000123,
        status=OrderStatus.FILLED,
        price=1.222,
        deal_type=DealType.base_order,
    ),
    ExchangeOrderTable(
        id=UUID(id),
        order_id="321",
        order_type=OrderType.limit,
        time_in_force="GTC",
        timestamp=0,
        order_side="sell",
        pair="BTCUSDC",
        qty=0.000123,
        status=OrderStatus.FILLED,
        price=1.222,
        deal_type=DealType.take_profit,
    ),
]


deal_table = DealTable(
    opening_price=1.3,
    opening_qty=0,
    opening_timestamp=0,
    current_price=0,
    take_profit_price=0,
    closing_timestamp=0,
    closing_price=0,
    closing_qty=0,
    trailing_stop_loss_price=0,
    trailing_profit_price=0,
    stop_loss_price=0,
    margin_loan_id=0,
)


mocked_db_data = BotTable(
    id=UUID(id),
    pair="ADXUSDC",
    fiat="USDC",
    fiat_order_size=15,
    candlestick_interval=BinanceKlineIntervals.fifteen_minutes,
    close_condition=CloseConditions.dynamic_trailing,
    dynamic_trailing=False,
    cooldown=360,
    created_at=ts,
    logs=[],
    mode="manual",
    name="coinrule_fast_and_slow_macd_2024-04-20T22:28",
    stop_loss=3.0,
    take_profit=2.3,
    trailing=True,
    trailing_deviation=3.0,
    trailing_profit=0.0,
    position=Position.long,
    updated_at=ts,
    status=Status.inactive,
    margin_short_reversal=False,
    deal=deal_table,
    orders=orders,
)
