from pydantic import BaseModel
from tools.handle_error import StandardResponse


class OrderParams(BaseModel):
    pair: str
    qty: float
    price: float


class OrderRequest(StandardResponse):
    data: OrderParams
