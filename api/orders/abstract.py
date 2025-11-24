from abc import ABC, abstractmethod
from time import time
from uuid import uuid4
from databases.crud.autotrade_crud import AutotradeCrud
from tools.enum_definitions import ExchangeId, OrderSide
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
        self.exchange_id: ExchangeId = self.autotrade_settings.exchange_id

    # Exchange-agnostic utility methods
    def generate_id(self):
        """Generate a UUID for order tracking"""
        return uuid4()

    def generate_short_id(self):
        """Generate a short numeric ID"""
        id = uuid4().int
        return int(str(id)[:8])

    def get_ts(self):
        """Get timestamp in milliseconds"""
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

    # Abstract methods that MUST be implemented by exchange-specific controllers
    @abstractmethod
    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available order price.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def buy_order(
        self, symbol: str, qty: float, price_precision: int = 0, qty_precision: int = 0
    ):
        """
        Execute a buy order on the exchange.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def sell_order(
        self, symbol: str, qty: float, price_precision: int = 0, qty_precision: int = 0
    ):
        """
        Execute a sell order on the exchange.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def delete_order(self, symbol: str, order_id: int):
        """
        Cancel a single order.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def delete_all_orders(self, symbol: str):
        """
        Cancel all open orders for a symbol.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def simulate_order(self, pair: str, side: OrderSide, qty=1):
        """
        Simulate an order without executing it.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def buy_margin_order(self, symbol: str, qty: float):
        """
        Execute a margin buy order.
        Exchange-specific implementation required (if supported).
        """
        pass

    @abstractmethod
    def sell_margin_order(self, symbol: str, qty: float):
        """
        Execute a margin sell order.
        Exchange-specific implementation required (if supported).
        """
        pass
