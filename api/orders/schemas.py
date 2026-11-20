from pydantic import BaseModel


class OrderParams(BaseModel):
    pair: str
    qty: float
    price: float
