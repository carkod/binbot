from abc import ABC
from time import time
from uuid import uuid4
from databases.crud.autotrade_crud import AutotradeCrud
from tools.maths import round_timestamp
from databases.crud.symbols_crud import SymbolsCrud


class OrderControllerAbstract(ABC):
    """
    Abstract base class for order controllers across different exchanges.

    Contains exchange-agnostic methods and defines the interface that
    all exchange-specific implementations must follow.
    """

    def __init__(self) -> None:
        # Common attributes for all exchanges
        self.price_precision: int
        self.qty_precision: int
        self.symbols_crud = SymbolsCrud()
        self.autotrade_settings = AutotradeCrud().get_settings()

    # Exchange-agnostic utility methods
    def generate_id(self):
        """
        Generate a UUID for order tracking
        """
        return uuid4()

    def generate_short_id(self):
        """
        Generate a short numeric ID
        """
        id = uuid4().int
        return int(str(id)[:8])

    def get_ts(self):
        """
        Get timestamp in milliseconds
        """
        return round_timestamp(time() * 1000)

    def calculate_price_precision(self, symbol: str) -> int:
        """
        Calculate the price precision for the symbol
        taking data from API db
        """
        symbol_info = self.symbols_crud.get_symbol(symbol)
        return symbol_info.price_precision

    def calculate_qty_precision(self, symbol: str) -> int:
        """
        Calculate the quantity precision for the symbol
        taking data from API db
        """
        symbol_info = self.symbols_crud.get_symbol(symbol)
        return symbol_info.qty_precision
