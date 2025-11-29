from exchange_apis.kucoin import KucoinApi
from account.abstract import AccountAbstract


class KucoinAccount(AccountAbstract):
    """
    KuCoin-specific implementation of AccountAbstract.

    Inherits common methods from AccountAbstract and
    KuCoin API methods from KucoinApi.
    """

    def __init__(self):
        self.api = KucoinApi()

    def calculate_total_commissions(self, fee: str) -> float:
        """
        Calculate total commissions for a given order.

        Works for both exchanges with fallback for different field names
        (Binance uses 'commission', KuCoin uses 'fee')
        """
        return float(fee)

    def get_book_order_deep(self, symbol: str, order_side: bool) -> float:
        """
        Get deepest price to avoid market movements causing orders to fail
        which means bid/ask are flipped

        Buy order = get bid prices = True
        Sell order = get ask prices = False
        """
        # KuCoin uses size "20" or "100" for order book depth
        data = self.api.get_part_order_book(symbol, "20")
        if order_side:
            price, _ = data["bids"][0]
        else:
            price, _ = data["asks"][0]
        return float(price)

    def get_ticker_price(self, symbol: str):
        """
        Get ticker price for a symbol
        KuCoin symbol format: BTC-USDT (with hyphen)
        """
        # Note: This would need to be implemented in KucoinApi
        # For now, returning a placeholder
        # The KuCoin SDK would need get_ticker or similar method
        raise NotImplementedError(
            "get_ticker_price needs to be implemented in KucoinApi"
        )

    def get_raw_balance(self) -> list:
        """
        Unrestricted balance
        KuCoin returns accounts with different structure than Binance
        """
        # Note: This would need to be implemented in KucoinApi
        # KuCoin uses get_account_list() to get all accounts
        raise NotImplementedError(
            "get_raw_balance needs to be implemented in KucoinApi"
        )

    def get_single_spot_balance(self, asset) -> float:
        """
        Get single asset spot balance
        """
        # Note: This would need to be implemented in KucoinApi
        raise NotImplementedError(
            "get_single_spot_balance needs to be implemented in KucoinApi"
        )

    def get_single_raw_balance(self, asset, fiat="USDC") -> float:
        """
        Get both SPOT balance and ISOLATED MARGIN balance
        """
        # Note: This would need to be implemented in KucoinApi
        # KuCoin has different margin structure than Binance
        raise NotImplementedError(
            "get_single_raw_balance needs to be implemented in KucoinApi"
        )

    def get_margin_balance(self, symbol="BTC") -> float:
        """
        Get margin balance for a symbol
        """
        # Note: KuCoin margin API structure differs from Binance
        raise NotImplementedError(
            "get_margin_balance needs to be implemented in KucoinApi"
        )

    def match_qty_engine(self, symbol: str, order_side: bool, qty: float = 1) -> float:
        """
        Similar to matching_engine,
        it is used to find a price that matches the quantity provided
        so qty != 0

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        @param: qty - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.api.get_part_order_book(symbol, "100")
        if order_side:
            total_length = len(data["asks"])
        else:
            total_length = len(data["bids"])

        price, base_qty = self._get_price_from_book_order(data, order_side, 0)

        buyable_qty = float(qty) / float(price)
        if buyable_qty < base_qty:
            return base_qty
        else:
            for i in range(1, total_length):
                price, base_qty = self._get_price_from_book_order(data, order_side, i)
                if buyable_qty > base_qty:
                    return base_qty
                else:
                    continue
            raise Exception("Not enough liquidity to match the order quantity")

    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell

        _get_price_from_book_order previously did max 100 ask/bid levels,
        however that causes trading price to be too far from market price,
        therefore incurring in impossible sell or losses.
        Setting it to 10 levels max to avoid drifting too much from market price.

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        @param: qty - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.api.get_part_order_book(symbol, "20")
        price, base_qty = self._get_price_from_book_order(data, order_side, 0)

        if qty == 0:
            return price
        else:
            buyable_qty = float(qty) / float(price)
            if buyable_qty < base_qty:
                return price
            else:
                for i in range(1, 11):
                    price, base_qty = self._get_price_from_book_order(
                        data, order_side, i
                    )
                    if buyable_qty > base_qty:
                        return price
                    else:
                        continue
                # caller to use market price
                return 0
