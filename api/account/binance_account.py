from apis import BinbotApi
from account.abstract import AccountAbstract


class BinanceAccount(AccountAbstract):
    """
    Binance-specific implementation of AccountAbstract.

    Inherits common methods from AccountAbstract and
    Binance API methods from BinbotApi.
    """

    def __init__(self):
        self.api = BinbotApi()

    def get_book_order_deep(self, symbol: str, order_side: bool) -> float:
        """
        Get deepest price to avoid market movements causing orders to fail
        which means bid/ask are flipped

        Buy order = get bid prices = True
        Sell order = get ask prices = False
        """
        data = self.api.get_book_depth(symbol)
        if order_side:
            price, _ = data["bids"][0]
        else:
            price, _ = data["asks"][0]
        return float(price)

    def get_raw_balance(self) -> list:
        """
        Unrestricted balance
        """
        data = self.api.get_account_balance()
        balances = []
        for item in data["balances"]:
            if float(item["free"]) > 0 or float(item["locked"]) > 0:
                balances.append(item)
        return balances

    def get_single_spot_balance(self, asset) -> float:
        data = self.api.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
        return 0

    def get_single_raw_balance(self, asset, fiat="USDC") -> float:
        """
        Get both SPOT balance and ISOLATED MARGIN balance
        """
        data = self.api.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
        else:
            symbol = asset + fiat
            data = self.api.get_isolated_balance(symbol)
            if len(data) > 0:
                qty = float(data[0]["baseAsset"]["free"]) + float(
                    data[0]["baseAsset"]["borrowed"]
                )
                if qty > 0:
                    return qty
        return 0

    def get_margin_balance(self, symbol="BTC") -> float:
        # Response after request
        data = self.api.get_isolated_balance(symbol)
        symbol_balance = next((x["free"] for x in data if x["asset"] == symbol), 0)
        return symbol_balance

    def match_qty_engine(self, symbol: str, order_side: bool, qty: float = 1) -> float:
        """
        Similar to matching_engine,
        it is used to find a price that matches the quantity provided
        so qty != 0

        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        @param: base_order_size - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.api.get_book_depth(symbol)
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
        @param: base_order_size - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.api.get_book_depth(symbol)
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
