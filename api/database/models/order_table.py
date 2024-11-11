from tools.enum_definitions import DealType
from sqlmodel import Field, SQLModel


class ExchangeOrderTable(SQLModel, table=True):
    """
    Data provided by Crypto Exchange,
    therefore they should be all be strings

    This should be an immutable source of truth
    whatever shape comes from third party provider,
    should be stored the same way
    """
    id: int | None = Field(default=None, primary_key=True)
    order_type: str
    time_in_force: str
    timestamp: str | int
    order_id: str | int
    order_side: str
    pair: str
    fills: list
    qty: str | float
    status: str
    price: str | float
    deal_type: DealType
