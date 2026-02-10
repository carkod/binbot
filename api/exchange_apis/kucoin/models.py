from pybinbot import BotBase
from pydantic import Field


class FuturesBot(BotBase):
    """
    Bot model for futures trading, inherits from BotBase.
    Can add futures-specific parameters here if needed.
    """

    leverage: int = Field(default=1, ge=1, description="Leverage for futures trading")
    contracts: int = Field(
        default=0, ge=0, description="Number of futures contracts to trade"
    )
