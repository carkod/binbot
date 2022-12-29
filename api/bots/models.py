from time import time
from bson.objectid import ObjectId
from deals.models import DealModel, OrderModel
from tools.enum_definitions import BinbotEnums


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
        status=0,
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
        self.status = status
