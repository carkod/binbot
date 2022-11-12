from time import time
from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from api.deals.schema import DealSchema, OrderSchema
from api.tools.enum_definitions import EnumDefinitions

class SafetyOrderSchema(Schema):
    name: str = fields.Str(required=True, dump_default="so_1") # should be so_<index>
    status: str = fields.Int(dump_default=0) # 0 = standby, safety order hasn't triggered, 1 = filled safety order triggered, 2 = error
    order_id: str = fields.Str(dump_default="")
    created_at: float = fields.Float(dump_default=time() * 1000)
    updated_at: float = fields.Float(dump_default=time() * 1000)
    buy_price: float = fields.Float(required=True, dump_default=0) # base currency quantity e.g. 3000 USDT in BTCUSDT
    buy_timestamp: float = fields.Float(dump_default=0)
    so_size: float = fields.Float(required=True, dump_default=0) # quote currency quantity e.g. 0.00003 BTC in BTCUSDT 
    max_active_so: float = fields.Float(dump_default=0)
    so_volume_scale: float = fields.Float(dump_default=0)
    so_step_scale: float = fields.Float(dump_default=0)
    so_asset: str = fields.Str(dump_default="USDT")
    errors: list[str] = fields.List(fields.Str(), dump_default=[])
    total_commission: float = fields.Float(dump_default=0)

class BotSchema(Schema):
    balance_size_to_use: float= fields.Float()
    balance_to_use: str = fields.Str(required=True)
    base_order_size: str = fields.Str(required=True) # Min Binance 0.0001 BNB
    candlestick_interval: str = fields.Str(required=True)
    cooldown: int = fields.Int() # cooldown period before opening next bot with same pair
    created_at = fields.Float()
    deal = fields.Nested(DealSchema)
    errors: list[str] = fields.List(fields.Str)
    locked_so_funds: float = fields.Float() # funds locked by Safety orders
    mode = fields.Str(dump_default="manual") # ["manual", "autotrade"]. Manual is triggered by the terminal dashboard, autotrade by research app
    name = fields.Str(dump_default="Default bot")
    orders: list = fields.List(fields.Nested(OrderSchema)) # Internal
    pair = fields.Str(required=True)
    status = fields.Str(required=True, dump_default="inactive", validate=OneOf(EnumDefinitions.statuses))
    stop_loss: float = fields.Float()
    take_profit: float = fields.Float(required=True)
    trailling: str = fields.Str(required=True)
    trailling_deviation: float = fields.Float(required=True)
    trailling_profit: float = fields.Float() # Trailling activation (first take profit hit)
    safety_orders = fields.List(fields.Nested(SafetyOrderSchema))
    strategy = fields.Str(required=True, dump_default="long", validate=OneOf(["long", "short"]))
    short_buy_price = fields.Float() # > 0 base_order does not execute immediately, executes short strategy when this value is hit
    short_sell_price = fields.Float() # autoswitch to short_strategy
    # Deal and orders are internal, should never be updated by outside data
    total_commission: float = fields.Float()
    updated_at = fields.Float()
    _id = fields.Str()
