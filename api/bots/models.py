from time import time
from bson.objectid import ObjectId
from api.deals.models import DealModel
from api.tools.enum_definitions import EnumDefinitions


class BotSchemaValidation(Exception):
    pass

class SafetyOrderModel:
    def __init__(
        self,
        buy_price,
        so_size,
        name="so_1",
        order_id="",
        buy_timestamp=0,
        errors=[],
        total_comission=0,
        so_volume_scale=0,
        created_at=time() * 1000,
        updated_at=time() * 1000,
        *args,
        **kwargs
    ):
        self.name: str = name  # should be so_<index>
        self.order_id: str = order_id
        self.created_at: float = created_at
        self.updated_at: float = updated_at
        self.buy_price: float = buy_price
        self.buy_timestamp: float = buy_timestamp
        self.so_size: float = so_size
        self.errors: list[str] = errors
        self.total_commission: float = float(total_comission)
        self.so_volume_scale = so_volume_scale

class BotModel:
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """
    def __init__(
        self,
        pair: str,
        base_order_size: str,
        _id = None,
        created_at = time() * 1000,
        updated_at = time() * 1000,
        take_profit: float = 3,
        status: str = EnumDefinitions.statuses[0],
        name: str = "Default bot",
        mode: str = "manual",
        balance_size_to_use: float = 0,
        balance_to_use: str = "USDT",
        candlestick_interval: str = "15m",
        trailling: str = "false",
        trailling_deviation: float = 0.63,
        trailling_profit: float = 0, # Trailling activation (first take profit hit),
        orders: list = [], # Internal
        stop_loss: float = 0,
        # Deal and orders are internal, should never be updated by outside data,
        deal: object = {},
        errors: list[str] = [],
        total_commission: float = 0,
        cooldown: float = 0,
        # Safety orders,
        locked_so_funds: float = 0,
        safety_orders = [],
        *args,
        **kwargs
    ) -> None:
        self.balance_size_to_use = balance_size_to_use
        self.balance_to_use = balance_to_use
        self.base_order_size = base_order_size
        self.candlestick_interval = candlestick_interval
        self.cooldown = cooldown
        self.created_at = created_at
        self.deal = DealModel(**deal)
        self.errors = errors
        self.locked_so_funds = locked_so_funds
        self.mode = mode
        self.name = name
        self._id = _id or ObjectId()
        self.orders = orders
        self.pair = pair
        self.safety_orders = self.append_so(safety_orders)
        self.status = status
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.total_commission = total_commission
        self.trailling = trailling
        self.trailling_deviation = trailling_deviation
        self.trailling_profit = trailling_profit
        self.updated_at = updated_at

    def append_so(self, so_list):
        safety_orders = []
        for so in so_list:
            so_model = SafetyOrderModel(**so)
            safety_orders.append(so_model)
        return safety_orders
