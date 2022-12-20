from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from pydantic import BaseModel, EmailStr, Field
from api.tools.handle_error import PyObjectId

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
    

class AutotradeSettingsSchema(Schema):
    _id: str = fields.Str()
    updated_at: float = fields.Float()
    candlestick_interval: str = fields.Str()
    autotrade: int = fields.Int(required=True)
    trailling: str = fields.Str(required=True, validate=OneOf(["true", "false"]))
    trailling_deviation: float = fields.Float()
    trailling_profit: float = fields.Float()
    stop_loss: float = fields.Float()
    take_profit: float = fields.Float()
    balance_to_use: str = fields.Str()
    balance_size_to_use: str = fields.Float()
    max_request: int = fields.Int()
    system_logs: str = fields.List(fields.Str())
    update_required: bool = fields.Boolean()
    telegram_signals: int = fields.Int()
    max_active_autotrade_bots: int = fields.Int()
    base_order_size: str = fields.Str()
