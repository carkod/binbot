import json
from typing import TYPE_CHECKING
from pydantic import field_serializer, field_validator
from database.models.bot_table import BotBase
from tools.enum_definitions import (
    BinbotEnums,
)
from sqlmodel import Relationship

# avoids circular imports
# https://sqlmodel.tiangolo.com/tutorial/code-structure/#hero-model-file
if TYPE_CHECKING:
    from database.models.deal_table import DealTable
    from database.models.order_table import ExchangeOrderTable


class PaperTradingTable(BotBase, table=True):
    """
    Fake bots

    these trade without actual money, so qty
    is usually 0 or 1. Orders are simualted
    """

    __tablename__ = "paper_trading"

    deal: "DealTable" = Relationship(back_populates="bot")
    # filled up internally by Exchange
    orders: list["ExchangeOrderTable"] = Relationship(back_populates="bot")
