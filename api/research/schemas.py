from pydantic import BaseModel, Field
from tools.handle_error import StandardResponse

class BlacklistSchema(BaseModel):
    pair: str
    reason: str

    class Config:
        schema_extra = {
            "example": {
                "pair": "BNBBTC",
                "reason": "Overtraded",
            }
        }


class BlacklistResponse(StandardResponse):
    data: list[BlacklistSchema]


"""
Database control for symbols that are used
in signals.
"""
class SubscribedSymbolsSchema(BaseModel):
    _id: str
    pair: str
    blacklisted: bool = False
    blacklisted_reason: str = ""

    class Config:
        schema_extra = {
            "example": {
                "_id": "BNBBTC",
                "pair": "BNBBTC",
                "blacklisted": False,
                "blacklisted_reason": "Overtraded"
            }
        }


class SubscribedSymbolsResponse(StandardResponse):
    data: list[SubscribedSymbolsSchema]
