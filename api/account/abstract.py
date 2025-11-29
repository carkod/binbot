from abc import ABC, abstractmethod


class AccountAbstract(ABC):
    """
    Abstract base class for account operations across different exchanges.

    Defines the interface that all exchange-specific account implementations
    must follow (Binance, KuCoin, etc.)
    """

    def _get_price_from_book_order(self, data: dict, order_side: bool, index: int):
        """
        Extract price and quantity from order book at specific index.

        This implementation works for both Binance and KuCoin as they
        have similar order book structures: [["price", "qty"], ...]

        Buy order = get bid prices = True
        Sell order = get ask prices = False
        """
        if order_side:
            price, base_qty = data["bids"][index]
        else:
            price, base_qty = data["asks"][index]

        return float(price), float(base_qty)

    @abstractmethod
    def get_raw_balance(self) -> list:
        """
        Get unrestricted balance from exchange.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def get_single_spot_balance(self, asset) -> float:
        """
        Get single asset spot balance.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def get_single_raw_balance(self, asset, fiat="USDC") -> float:
        """
        Get both SPOT balance and ISOLATED MARGIN balance for an asset.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def get_margin_balance(self, symbol="BTC") -> float:
        """
        Get margin balance for a symbol.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def match_qty_engine(self, symbol: str, order_side: bool, qty: float = 1) -> float:
        """
        Find a price that matches the quantity provided.
        Exchange-specific implementation required.
        """
        pass

    @abstractmethod
    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available 100% fill order price.
        Exchange-specific implementation required.
        """
        pass
