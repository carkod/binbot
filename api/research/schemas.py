from pydantic import BaseModel, Field
from api.tools.handle_error import PyObjectId, StandardResponse

class BlacklistSchema(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
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
