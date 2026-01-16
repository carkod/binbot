from pydantic import BaseModel
from pybinbot import StandardResponse


class OrderParams(BaseModel):
    pair: str
    qty: float
    price: float


class OrderRequest(StandardResponse):
    data: OrderParams
