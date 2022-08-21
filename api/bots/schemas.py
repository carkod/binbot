from time import time
from marshmallow import Schema, fields, post_load, pre_dump
from marshmallow.validate import OneOf
from api.bots.models import BotModel
from api.deals.schema import DealSchema
from api.tools.enum_definitions import EnumDefinitions

class SafetyOrderSchema(Schema):
    name: str = fields.Str(required=True, dump_default="so_1") # should be so_<index>
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
    _id = fields.UUID()
    pair = fields.Str(required=True)
    status = fields.Str(required=True, dump_default="inactive", validate=OneOf(EnumDefinitions.statuses))
    name = fields.Str(dump_default="Default bot")
    created_at = fields.Float()
    updated_at = fields.Float()
    mode = fields.Str(dump_default="manual")
    base_order_size: str = fields.Str(required=True) # Min Binance 0.0001 BNB
    balance_to_use: str = fields.Str(required=True)
    candlestick_interval: str = fields.Str(required=True)
    take_profit: float = fields.Float(required=True)
    trailling: str = fields.Str(required=True)
    trailling_deviation: float = fields.Float(required=True)
    trailling_profit: float = fields.Float() # Trailling activation (first take profit hit)
    orders: list = fields.List(fields.Str) # Internal
    stop_loss: float = fields.Float()
    # Deal and orders are internal, should never be updated by outside data
    deal = fields.Nested(DealSchema)
    errors: list[str] = fields.List(fields.Str)
    total_commission: float = fields.Float()
    cooldown: int = fields.Int()
    # Safety orders
    locked_so_funds: float = fields.Float()
    safety_orders = fields.List(fields.Nested(SafetyOrderSchema))

