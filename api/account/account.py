import requests
from apis import BinbotApi
from tools.handle_error import (
    handle_binance_errors,
    json_response,
    json_response_message,
    json_response_error,
)
from decimal import Decimal
from db import setup_db
from requests_cache import CachedSession, MongoCache
from pymongo import MongoClient
import os
import pandas
class Account(BinbotApi):
    def __init__(self):
        self.db = setup_db()
        pass

    def setup_mongocache(self):
        mongo = MongoClient(
            host=os.getenv("MONGO_HOSTNAME"),
            port=int(os.getenv("MONGO_PORT")),
            authSource="admin",
            username=os.getenv("MONGO_AUTH_USERNAME"),
            password=os.getenv("MONGO_AUTH_PASSWORD"),
        )
        mongo_cache = MongoCache(connection=mongo)
        return mongo_cache

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
        session = CachedSession('http_cache', backend=mongo_cache, expire_after=1440)
        exchange_info_res = session.get(url=f"{self.exchangeinfo_url}", params=params)
        exchange_info = handle_binance_errors(exchange_info_res)
        return exchange_info

    def _ticker_price(self):
        r = requests.get(url=self.ticker_price_url)
        data = handle_binance_errors(r)
        return data

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

    def ticker_24(self, type: str = "FULL", symbol: str | None = None):
        """
        Weight 40 without symbol
        https://github.com/carkod/binbot/issues/438

        Using cache
        """
        url = self.ticker24_url
        params = {
            "type": type
        }
        if symbol:
            params["symbol"] = symbol
        
        # mongo_cache = self.setup_mongocache()
        # expire_after = 15m because candlesticks are 15m
        # session = CachedSession('ticker_24_cache', backend=mongo_cache, expire_after=15)
        res = requests.get(url=url, params=params)
        data = handle_binance_errors(res)
        return data

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
            (m for m in market["filters"] if m["filterType"] == "PRICE_FILTER"), None
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
        quantity_filter = next(
            (m for m in market["filters"] if m["filterType"] == "LOT_SIZE"), None
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
            (m for m in market["filters"] if m["filterType"] == "MIN_NOTIONAL"), None
        )
        return min_notional_filter[min_notional_limit]

    def get_qty_precision(self, pair):
        lot_size_by_symbol = self.lot_size_by_symbol(pair, "stepSize")
        qty_precision = -(
            Decimal(str(lot_size_by_symbol))
            .as_tuple()
            .exponent
        )
        return qty_precision
    
    def get_one_balance(self, symbol="BTC"):
        # Response after request
        data = self.bb_request(url=self.bb_balance_url)
        symbol_balance = next(
            (x["free"] for x in data["data"] if x["asset"] == symbol), None
        )
        return symbol_balance

    def matching_engine(self, symbol: str, order_side: bool, qty=None):
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell
        If it doesn't match, do split order
        @param: order_side -
            Buy order = get ask prices = True
            Sell order = get bids prices = False
        @param: qty - quantity wanted to be bought/sold
        """

        url = self.order_book_url
        params = [("symbol", symbol)]
        res = requests.get(url=url, params=params)
        data = handle_binance_errors(res)
        
        if order_side:
            df = pandas.DataFrame(data["bids"], columns=["price", "qty"])
        else:
            df = pandas.DataFrame(data["asks"], columns=["price", "qty"])

        df["qty"] = df["qty"].astype(float)

        # Test bots qty = None
        if not qty:
            return df["price"].iloc[0]

        # If quantity matches list
        df = df[:5]
        match_qty = df[df.qty > float(qty)]
        condition = df["qty"] > float(qty)
        if not condition.any():
            # force market order
            return None
        try:
            match_qty["price"].iloc[0]
        except IndexError as e:
            print(e)
            print(f'Matching engine error {match_qty["price"]}')

        final_qty = match_qty["price"].iloc[0]
        return final_qty

    def check_isolated_margin_exists(self, symbol):
        """
        Check in exchange info if asset can be isolate-traded

        For isolated margin, the "isMarginTradingAllowed" property
        is often "false". So the only reliable property is permissions
        """

        symbols = self._exchange_info(symbol)
        permissions = symbols["symbols"][0]["permissions"]
        for permission in permissions:
            if "TRD_GRP_" in permission or "MARGIN" in permission:
                return True
        return False
