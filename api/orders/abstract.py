from abc import ABC
from time import time
from uuid import uuid4
from databases.crud.autotrade_crud import AutotradeCrud
from tools.maths import round_timestamp
from databases.crud.symbols_crud import SymbolsCrud
from abc import abstractmethod
from typing import Any, Dict, List
from tools.enum_definitions import OrderSide


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

    # --- Order operations that combine all Exchange interfaces ---
    @abstractmethod
    def simulate_order(
        self, pair: str, side: OrderSide, qty: float = 1
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def simulate_response_order(
        self, pair: str, side: OrderSide, qty: float = 1
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def simulate_margin_order(self, pair: str, side: OrderSide) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def sell_order(self, symbol: str, qty: float) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def buy_order(self, symbol: str, qty: float) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def close_all_orders(self, symbol: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def buy_margin_order(self, symbol: str, qty: float) -> Dict[str, Any]:
        """Optional: override in margin-capable controllers."""
        raise NotImplementedError("Margin not supported for this controller")

    @abstractmethod
    def sell_margin_order(self, symbol: str, qty: float) -> Dict[str, Any]:
        """Optional: override in margin-capable controllers."""
        raise NotImplementedError("Margin not supported for this controller")

    # --- Account related helpers used via order controller ---
    @abstractmethod
    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        raise NotImplementedError

    @abstractmethod
    def match_qty_engine(self, symbol: str, order_side: bool, qty: float = 1) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_book_order_deep(self, symbol: str, order_side: bool) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_raw_balance(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_single_spot_balance(self, asset) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_single_raw_balance(self, asset, fiat: str = "USDC") -> float:
        raise NotImplementedError

    @abstractmethod
    def get_margin_balance(self, symbol: str = "BTC") -> float:
        raise NotImplementedError
