from bots.models import BotModel, OrderModel
from deals.models import DealModel
from bots.models import BotModelResponse

id = "02031768-fbb9-4cc7-b549-642f15ab787b"
ts = 1733973560249.0

active_pairs = ["BTCUSDC", "ETHUSDT", "ADAUSDT"]

deal_model = DealModel(
    current_price=0,
    take_profit_price=0,
    trailling_stop_loss_price=0,
    trailling_profit_price=0,
    stop_loss_price=0,
    total_interests=0,
    total_commissions=0,
    margin_loan_id=0,
    margin_repay_id=0,
    opening_price=1.3,
    opening_qty=0,
    opening_timestamp=0,
    closing_timestamp=0,
    closing_price=0,
    closing_qty=0,
)

initial_deal_model = DealModel(
    current_price=0,
    take_profit_price=0,
    trailling_stop_loss_price=0,
    trailling_profit_price=0,
    stop_loss_price=0,
    total_interests=0,
    total_commissions=0,
    margin_loan_id=0,
    margin_repay_id=0,
    opening_price=1.3,
    opening_qty=0,
    opening_timestamp=0,
    closing_timestamp=0,
    closing_price=0,
    closing_qty=0,
)

orders_model = [
    OrderModel(
        order_type="MARKET",
        time_in_force="GTC",
        timestamp=0,
        order_id=123,
        order_side="buy",
        pair="BTCUSDC",
        qty=0.000123,
        status="filled",
        price=1.222,
        deal_type="base_order",
    ),
    OrderModel(
        order_id=321,
        order_type="LIMIT",
        time_in_force="GTC",
        timestamp=0,
        order_side="sell",
        pair="BTCUSDC",
        qty=0.000123,
        status="filled",
        price=1.222,
        deal_type="take_profit",
    ),
]

mock_model_data = BotModel(
    id=id,
    pair="ADXUSDC",
    fiat="USDC",
    base_order_size=15,
    candlestick_interval="15m",
    dynamic_trailling=False,
    close_condition="dynamic_trailling",
    cooldown=360,
    created_at=ts,
    status="inactive",
    margin_short_reversal=False,
    logs=[],
    mode="manual",
    name="coinrule_fast_and_slow_macd_2024-04-20T22:28",
    stop_loss=3.0,
    take_profit=2.3,
    trailling=True,
    trailling_deviation=3.0,
    trailling_profit=0,
    strategy="long",
    updated_at=ts,
    orders=orders_model,
    deal=deal_model,
)

# new bots don't have orders because they are not activated
mock_model_data_without_orders = BotModel(
    id=id,
    pair="ADXUSDC",
    fiat="USDC",
    base_order_size=15,
    candlestick_interval="15m",
    status="inactive",
    margin_short_reversal=False,
    dynamic_trailling=False,
    close_condition="dynamic_trailling",
    cooldown=360,
    created_at=ts,
    logs=[],
    mode="manual",
    name="coinrule_fast_and_slow_macd_2024-04-20T22:28",
    stop_loss=3.0,
    take_profit=2.3,
    trailling=True,
    trailling_deviation=3.0,
    trailling_profit=0,
    strategy="long",
    updated_at=ts,
    orders=[],
    deal=initial_deal_model,
)


class DealFactoryMock:
    def __init__(self, bot: BotModel):
        pass

    def open_deal(self):
        bot_model = BotModel(**mock_model_data.model_dump())
        return bot_model

    def close_all(self):
        bot_model = BotModel(**mock_model_data.model_dump())
        return bot_model


mock_bot_model_response = BotModelResponse(
    pair="ADXUSDC",
    fiat="USDC",
    base_order_size=15,
    candlestick_interval="15m",
    dynamic_trailling=False,
    close_condition="dynamic_trailling",
    cooldown=360,
    created_at=ts,
    status="inactive",
    margin_short_reversal=False,
    logs=[],
    mode="manual",
    name="coinrule_fast_and_slow_macd_2024-04-20T22:28",
    stop_loss=3.0,
    take_profit=2.3,
    trailling=True,
    trailling_deviation=3.0,
    trailling_profit=0,
    strategy="long",
    updated_at=ts,
    orders=orders_model,
    deal=deal_model,
)
