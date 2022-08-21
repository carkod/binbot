from time import time
from marshmallow import Schema, fields, post_load

class OrderSchema(Schema):
    deal_type = fields.Str()
    order_id = fields.Str()
    pair = fields.Str()
    order_side = fields.Str()
    order_type = fields.Str()
    price = fields.Str()
    qty = fields.Str()
    fills = fields.Str()
    time_in_force = fields.Str()
    status = fields.Str()

class DealSchema(Schema):
    order_id: int = fields.Int(dump_default=0) # should be so_<index>
    buy_timestamp: float = fields.Float(dump_default=0)
    buy_total_qty: float = fields.Float(dump_default=0)
    current_price: float = fields.Float(dump_default=0)
    buy_price: float = fields.Float(required=True, dump_default=0) # base currency quantity e.g. 3000 USDT in BTCUSDT
    avg_buy_price: float = fields.Float(dump_default=0) # same as buy_price but a copy for safety orders
    take_profit_price: float = fields.Float(dump_default=0) # quote currency quantity e.g. 0.00003 BTC in BTCUSDT 
    so_prices: float = fields.Float(dump_default=0)
    sell_timestamp: float = fields.Float(dump_default=0)
    sell_price: float = fields.Float(dump_default=0)
    sell_qty: float = fields.Float(dump_default=0)
    post_closure_current_price: float = fields.Float(dump_default=0)
    total_commission: float = fields.Float(dump_default=0)
