from pydantic import BaseModel


class Order(BaseModel):
    user_id: int
    status: str


class Order_detail(BaseModel):
    order_id: int
    product_id: int
    quantity: int


class Product(BaseModel):
    product_name: str
    default_price: float
    currency: str
    description: str
    images: str
    unit_label: str


class User(BaseModel):
    first_name: str
    last_name: str
    user_email: str
