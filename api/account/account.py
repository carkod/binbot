import requests
from apis import BinbotApi
from tools.handle_error import handle_binance_errors
from tools.maths import round_numbers


class Account(BinbotApi):
    def __init__(self):
        pass

    def _get_price_from_book_order(self, data: dict, order_side: bool, index: int):
        """
        Buy order = get bid prices = True
        Sell order = get ask prices = False
        """
        if order_side:
            price, base_qty = data["bids"][index]
        else:
            price, base_qty = data["asks"][index]

        return float(price), float(base_qty)

    def get_ticker_price(self, symbol: str):
        params = {"symbol": symbol}
        res = requests.get(url=self.ticker_price_url, params=params)
        data = handle_binance_errors(res)
        return data["price"]

    def get_raw_balance(self) -> list:
        """
        Unrestricted balance
        """
        data = self.get_account_balance()
        balances = []
        for item in data["balances"]:
            if float(item["free"]) > 0 or float(item["locked"]) > 0:
                balances.append(item)
        return balances

    def get_single_spot_balance(self, asset) -> float:
        data = self.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
        return 0

    def get_single_raw_balance(self, asset, fiat="USDC") -> float:
        """
        Get both SPOT balance and ISOLATED MARGIN balance
        """
        data = self.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
        else:
            symbol = asset + fiat
            data = self.get_isolated_balance(symbol)
            if len(data) > 0:
                qty = float(data[0]["baseAsset"]["free"]) + float(
                    data[0]["baseAsset"]["borrowed"]
                )
                if qty > 0:
                    return qty
        return 0

    def get_margin_balance(self, symbol="BTC") -> float:
        # Response after request
        data = self.get_isolated_balance(symbol)
        symbol_balance = next((x["free"] for x in data if x["asset"] == symbol), 0)
        return symbol_balance

    def get_book_order_deep(self, symbol: str, order_side: bool) -> float:
        """
        Get deepest price to avoid market movements causing orders to fail
        which means bid/ask are flipped

        Buy order = get bid prices = True
        Sell order = get ask prices = False
        """
        data = self.get_book_depth(symbol)
        if order_side:
            price, _ = data["bids"][0]
        else:
            price, _ = data["asks"][0]
        return float(price)

    def matching_engine(self, symbol: str, order_side: bool, qty: float = 0) -> float:
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell
        If it doesn't match, do split order
        @param: order_side -
            Buy order = get bid prices = False
            Sell order = get ask prices = True
        @param: base_order_size - quantity wanted to be bought/sold in fiat (USDC at time of writing)
        """
        data = self.get_book_depth(symbol)

        price, base_qty = self._get_price_from_book_order(data, order_side, 0)

        if qty == 0:
            return price
        else:
            buyable_qty = float(qty) / float(price)
            if buyable_qty < base_qty:
                return price
            else:
                total_length = len(data["bids"])
                for i in range(1, total_length):
                    price, base_qty = self._get_price_from_book_order(
                        data, order_side, i
                    )
                    if buyable_qty > base_qty:
                        return price
                    else:
                        continue
                raise ValueError(
                    "Unable to match base_order_size with available order prices"
                )

    def calculate_total_commissions(self, fills: dict) -> float:
        """
        Calculate total commissions for a given order
        """
        total_commission: float = 0
        for chunk in fills:
            total_commission += round_numbers(float(chunk["commission"]))
        return total_commission
