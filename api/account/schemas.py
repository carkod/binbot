from datetime import datetime
from pydantic import BaseModel
from api.tools.handle_error import StandardResponse


class BalanceSchema(BaseModel):
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """

    time: str = datetime.utcnow().strftime("%Y-%m-%d")
    balances: list = []
    estimated_total_usdt: float = 0


class BalanceResponse(StandardResponse):
    data: list[BalanceSchema]

class ListSymbolsResponse(StandardResponse):
    data: list[str]

class BinanceBalanceResponse(BaseModel):
    asset: str
    free: float
    locked: float
