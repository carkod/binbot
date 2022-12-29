from pydantic import BaseModel, Field
from tools.handle_error import StandardResponse

class BlacklistSchema(BaseModel):
    _id: str
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
