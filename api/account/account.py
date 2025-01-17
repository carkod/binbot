import requests
import os
from apis import BinbotApi
from tools.handle_error import (
    handle_binance_errors,
    json_response,
    json_response_message,
    json_response_error,
)
from database.db import setup_db
from requests_cache import CachedSession, MongoCache
from pymongo import MongoClient
from decimal import Decimal


class Account(BinbotApi):
    db = setup_db()

    def __init__(self):
        pass

    def setup_mongocache(self):
        mongo: MongoClient = MongoClient(
            host=os.getenv("MONGO_HOSTNAME"),
            port=int(os.getenv("MONGO_PORT", 2017)),
            authSource="admin",
            username=os.getenv("MONGO_AUTH_USERNAME"),
            password=os.getenv("MONGO_AUTH_PASSWORD"),
        )
        mongo_cache = MongoCache(connection=mongo)
        return mongo_cache

    def calculate_price_precision(self, symbol) -> int:
        precision = -1 * (
            Decimal(str(self.price_filter_by_symbol(symbol, "tickSize")))
            .as_tuple()
            .exponent
        )
        price_precision = int(precision)
        return price_precision

    def calculate_qty_precision(self, symbol) -> int:
        precision = -1 * (
            Decimal(str(self.lot_size_by_symbol(symbol, "stepSize")))
            .as_tuple()
            .exponent
        )
        qty_precision = int(precision)
        return qty_precision

    def _exchange_info(self, symbol=None):
        """
        This must be a separate method because classes use it with inheritance

        This request is used in many places to retrieve data about symbols, precisions etc.
        It is a high weight endpoint, thus Binance could ban our IP
        However it is not real-time updated data, so cache is used to avoid hitting endpoint
        too many times and still be able to re-request data everywhere.

        In addition, it uses MongoDB, with a separate database called "mongo_cache"
        """
        params = {}
        if symbol:
            params["symbol"] = symbol

        mongo_cache = self.setup_mongocache()
        # set up a cache that expires in 1440'' (24hrs)
        session = CachedSession("http_cache", backend=mongo_cache, expire_after=1440)
        exchange_info_res = session.get(url=f"{self.exchangeinfo_url}", params=params)
        exchange_info = handle_binance_errors(exchange_info_res)
        return exchange_info

    def _ticker_price(self):
        r = requests.get(url=self.ticker_price_url)
        data = handle_binance_errors(r)
        return data

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

    def ticker(self, symbol: str | None = None, json: bool = True):
        params = {}
        if symbol:
            params = {"symbol": symbol}
        res = requests.get(url=self.ticker_price_url, params=params)
        data = handle_binance_errors(res)
        if json:
            return json_response({"data": data})
        else:
            return data

    def get_ticker_price(self, symbol: str):
        params = {"symbol": symbol}
        res = requests.get(url=self.ticker_price_url, params=params)
        data = handle_binance_errors(res)
        return data["price"]

    def find_quoteAsset(self, symbol):
        """
        e.g. BNBBTC: base asset = BTC
        """
        symbols = self._exchange_info(symbol)
        quote_asset = symbols["symbols"][0]
        if quote_asset:
            quote_asset = quote_asset["quoteAsset"]
        return quote_asset

    def find_baseAsset(self, symbol):
        """
        e.g. BNBBTC: base asset = BNB
        """
        symbols = self._exchange_info(symbol)
        base_asset = symbols["symbols"][0]["baseAsset"]
        return base_asset

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
        symbols = self._ticker_price()
        symbols_list = [x["symbol"] for x in symbols]
        symbols_list.sort()
        return json_response({"data": symbols_list})

    def get_no_cannibal_symbols(self):
        """
        Raw symbols without active bots
        """
        symbols = self._ticker_price()
        symbols_list = [x["symbol"] for x in symbols]
        active_symbols = list(self.db.bot.find({"status": "active"}))

        no_cannibal_list = [x for x in symbols_list if x not in active_symbols]
        return json_response({"data": no_cannibal_list, "count": len(no_cannibal_list)})

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

    def price_filter_by_symbol(self, symbol, filter_limit):
        """
        PRICE_FILTER restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - filter_limit: string - minPrice or maxPrice
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        price_filter = next(
            (m for m in market["filters"] if m["filterType"] == "PRICE_FILTER")
        )
        return price_filter[filter_limit].rstrip(".0")

    def lot_size_by_symbol(self, symbol, lot_size_limit):
        """
        LOT_SIZE (quantity) restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - lot_size_limit: string - minQty, maxQty, stepSize
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        quantity_filter: list = next(
            (m for m in market["filters"] if m["filterType"] == "LOT_SIZE")
        )
        return quantity_filter[lot_size_limit].rstrip(".0")

    def min_notional_by_symbol(self, symbol, min_notional_limit="minNotional"):
        """
        MIN_NOTIONAL (price x quantity) restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - min_notional_limit: string - minNotional
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        min_notional_filter = next(
            (m for m in market["filters"] if m["filterType"] == "MIN_NOTIONAL")
        )
        return min_notional_filter[min_notional_limit]

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

    def get_single_raw_balance(self, asset) -> float:
        data = self.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
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
            Buy order = get bid prices = True
            Sell order = get ask prices = False
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
