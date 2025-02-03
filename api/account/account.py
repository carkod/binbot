import requests
from apis import BinbotApi
from tools.handle_error import (
    handle_binance_errors,
    json_response,
    json_response_message,
    json_response_error,
)


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

    def find_base_asset_json(self, symbol):
        data = self.find_baseAsset(symbol)
        return json_response({"data": data})

    def find_quote_asset_json(self, symbol):
        data = self.find_quoteAsset(symbol)
        return json_response({"data": data})

    def find_market(self, quote):
        symbols = self._exchange_info()
        market = [
            symbol["symbol"]
            for symbol in symbols["symbols"]
            if symbol["baseAsset"] == quote
        ]
        if len(market) > 1:
            # Match BTC first
            # DUSKBNB does not exist in the market but provided (Binance bug?)
            match_btc = next((s for s in market if "BTC" in s), None)
            if match_btc:
                return match_btc
            match_bnb = next((s for s in market if "BNB" in s), None)
            if match_bnb:
                return match_bnb
            return market[0]

    def get_symbol_info(self, pair):
        symbols = self._exchange_info(pair)
        if not symbols:
            return json_response_error("Symbol not found!")
        symbol = symbols["symbols"][0]
        if symbol:
            return json_response({"data": symbol})
        else:
            return json_response_message("Pair not found")

    def get_symbols(self):
        symbols = self.ticker()
        symbols_list = [x["symbol"] for x in symbols]
        symbols_list.sort()
        return json_response({"data": symbols_list})

    def get_quote_asset_precision(self, symbol, quote=True):
        """
        Get Maximum precision (maximum number of decimal points)
        @params quote: boolean - quote=True, base=False
        @params symbol: string - market e.g. BNBBTC
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        asset_precision = (
            market["quoteAssetPrecision"] if quote else market["baseAssetPrecision"]
        )
        return asset_precision

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

    def get_single_raw_balance(self, asset, fiat="USDC") -> float:
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
            buyable_qty = qty / float(price)
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
            total_commission += float(chunk["commission"])
        return total_commission
