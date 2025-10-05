from databases.tables.bot_table import BotTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable
from tools.enum_definitions import DealType, OrderType
from uuid import UUID

ts = 1733973560249.0
id = "02031768-fbb9-4cc7-b549-642f15ab787b"

orders = [
    ExchangeOrderTable(
        id=id,
        order_id=123,
        order_type=OrderType.market,
        time_in_force="GTC",
        timestamp=0,
        order_side="buy",
        pair="BTCUSDC",
        qty=0.000123,
        status="filled",
        price=1.222,
        deal_type=DealType.base_order,
        total_commission=0,
    ),
    ExchangeOrderTable(
        id=id,
        order_id=321,
        order_type=OrderType.limit,
        time_in_force="GTC",
        timestamp=0,
        order_side="sell",
        pair="BTCUSDC",
        qty=0.000123,
        status="filled",
        price=1.222,
        deal_type=DealType.take_profit,
        total_commission=0,
    ),
]


deal_table = DealTable(
    opening_price=1.3,
    opening_qty=0,
    opening_timestamp=0,
    current_price=0,
    sd=0,
    avg_opening_price=0,
    take_profit_price=0,
    sell_timestamp=0,
    sell_price=0,
    sell_qty=0,
    trailling_stop_loss_price=0,
    trailling_profit_price=0,
    stop_loss_price=0,
    trailling_profit=0,
    short_sell_price=0,
    margin_loan_id=0,
)


mocked_db_data = BotTable(
    id=UUID(id),
    pair="ADXUSDC",
    fiat="USDC",
    base_order_size=15,
    opening_price=1.222,
    candlestick_interval="15m",
    close_condition="dynamic_trailling",
    dynamic_trailling=False,
    cooldown=360,
    created_at=ts,
    logs=[],
    mode="manual",
    name="coinrule_fast_and_slow_macd_2024-04-20T22:28",
    stop_loss=3.0,
    take_profit=2.3,
    trailling=True,
    trailling_deviation=3.0,
    trailling_profit=0.0,
    strategy="long",
    updated_at=ts,
    status="inactive",
    margin_short_reversal=False,
    deal=deal_table,
    orders=orders,
)
