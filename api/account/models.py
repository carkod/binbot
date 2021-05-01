import hashlib
import hmac
import json
import os
import time as tm
from urllib.parse import urlparse

import pandas as pd
import requests
from flask import current_app as app, request
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from api.tools.round_numbers import proper_round
from api.tools.ticker import Conversion
from datetime import datetime, timedelta
from bson.objectid import ObjectId


class Account:

    recvWindow = os.getenv("RECV_WINDOW")
    secret = os.getenv("BINANCE_SECRET")
    key = os.getenv("BINANCE_KEY")
    account_url = os.getenv("ACCOUNT")
    exchangeinfo_url = os.getenv("EXCHANGE_INFO")
    ticker_price = os.getenv("TICKER_PRICE")
    ticker24_url = os.getenv("TICKER24")

    def __init__(self):
        url = self.exchangeinfo_url
        self._exchange_info = requests.get(url=url).json()

    def request_data(self):
        timestamp = int(round(tm.time() * 1000))
        # Get data for a single crypto e.g. BTT in BNB market
        params = {"recvWindow": self.recvWindow, "timestamp": timestamp}
        headers = {"X-MBX-APIKEY": self.key}
        url = self.account_url

        # Prepare request for signing
        r = requests.Request("GET", url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(
            self.secret.encode("utf-8"), total_params.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature

        # Response after request
        res = requests.get(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def _ticker_price(self):
        url = self.ticker_price
        r = requests.get(url=url)
        return r.json()

    def ticker(self):
        url = self.ticker_price
        symbol = request.view_args["symbol"]
        params = {}
        if symbol:
            params = {"symbol": symbol}
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        resp = jsonResp({"data": data}, 200)
        return resp

    def get_ticker_price(self, symbol):
        url = self.ticker_price
        params = None
        if symbol:
            params = {"symbol": symbol}
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        return data["price"]

    def ticker_24(self):
        url = self.ticker24_url
        symbol = request.view_args["symbol"]
        params = {"symbol": symbol}
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        resp = jsonResp({"data": data}, 200)
        return resp

    def get_balances(self):
        data = self.request_data()["balances"]
        df = pd.DataFrame(data)
        df["free"] = pd.to_numeric(df["free"])
        df["asset"] = df["asset"].astype(str)
        df.drop("locked", axis=1, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # Get table with > 0
        balances = df[df["free"] > 0.000000].to_dict("records")

        # filter out empty
        # Return response
        resp = jsonResp(balances, 200)
        return resp

    def get_balances_btc(self):
        data = self.request_data()["balances"]
        df = pd.DataFrame(data)
        df["free"] = pd.to_numeric(df["free"])
        df["asset"] = df["asset"].astype(str)
        df.drop("locked", axis=1, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # Get table with > 0
        balances = df[df["free"] > 0.000000].to_dict("records")
        data = {"total_btc": 0, "balances": []}
        for b in balances:
            symbol = self.find_market(b["asset"])
            market = self.find_quoteAsset(symbol)
            rate = 0
            if b["asset"] != "BTC":
                rate = self.get_ticker_price(symbol)

                if "locked" in b:
                    qty = b["free"] + b["locked"]
                else:
                    qty = b["free"]

                btc_value = float(qty) * float(rate)

                # Non-btc markets
                if market != "BTC" and b["asset"] != "USDT":
                    x_rate = self.get_ticker_price(market + "BTC")
                    x_value = float(qty) * float(rate)
                    btc_value = float(x_value) * float(x_rate)
                
                # Only tether coins for hedging
                if b["asset"] == "USDT":
                    rate = self.get_ticker_price("BTCUSDT")
                    btc_value = float(qty) / float(rate)

            else:
                if "locked" in b:
                    btc_value = b["free"] + b["locked"]
                else:
                    btc_value = b["free"]

            data["total_btc"] += btc_value
            assets = {"asset": b["asset"], "btc_value": btc_value}
            data["balances"].append(assets)

        # filter out empty
        # Return response
        resp = jsonResp(data, 200)
        return resp

    def get_one_balance(self, symbol="BTC"):
        data = json.loads(self.get_balances().data)
        return next((x["free"] for x in data if x["asset"] == symbol), None)

    def find_quoteAsset(self, symbol):
        symbols = self._exchange_info["symbols"]
        quote_asset = next((s for s in symbols if s["symbol"] == symbol), None)[
            "quoteAsset"
        ]
        return quote_asset

    def find_baseAsset(self, symbol):
        symbols = self._exchange_info["symbols"]
        base_asset = next((s for s in symbols if s["symbol"] == symbol), None)[
            "baseAsset"
        ]
        return base_asset

    def find_base_asset_json(self, symbol):
        data = self.find_baseAsset(symbol)
        return jsonResp({"data": data}, 200)

    def find_quote_asset_json(self, symbol):
        data = self.find_quoteAsset(symbol)
        return jsonResp({"data": data}, 200)

    def find_market(self, quote):
        symbols = self._exchange_info["symbols"]
        market = next((s for s in symbols if s["baseAsset"] == quote), None)["symbol"]
        return market

    def get_symbol_info(self):
        symbols = self._exchange_info["symbols"]
        pair = request.view_args["pair"]
        symbol = next((s for s in symbols if s["symbol"] == pair), None)
        if symbol:
            return jsonResp({"data": symbol}, 200)
        else:
            return jsonResp_message("Pair not found", 200)

    def get_symbols(self):
        symbols = self._ticker_price()
        symbols_list = [x["symbol"] for x in symbols]
        symbols_list.sort()
        return jsonResp({"data": symbols_list}, 200)

    def get_quote_asset_precision(self, symbol, quote=True):
        """
        Get Maximum precision (maximum number of decimal points)
        @params quote: boolean - quote=True, base=False
        @params symbol: string - market e.g. BNBBTC
        """
        symbols = self._exchange_info["symbols"]
        market = next((s for s in symbols if s["symbol"] == symbol), None)
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
        symbols = self._exchange_info["symbols"]
        market = next((s for s in symbols if s["symbol"] == symbol), None)
        price_filter = next(
            (m for m in market["filters"] if m["filterType"] == "PRICE_FILTER"), None
        )
        return price_filter[filter_limit].rstrip('.0')

    def lot_size_by_symbol(self, symbol, lot_size_limit):
        """
        LOT_SIZE (quantity) restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - lot_size_limit: string - minQty, maxQty, stepSize
        """
        symbols = self._exchange_info["symbols"]
        market = next((s for s in symbols if s["symbol"] == symbol), None)
        quantity_filter = next(
            (m for m in market["filters"] if m["filterType"] == "LOT_SIZE"), None
        )
        return quantity_filter[lot_size_limit].rstrip('.0')

    def min_notional_by_symbol(self, symbol, min_notional_limit="minNotional"):
        """
        MIN_NOTIONAL (price x quantity) restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - min_notional_limit: string - minNotional
        """
        symbols = self._exchange_info["symbols"]
        market = next((s for s in symbols if s["symbol"] == symbol), None)
        min_notional_filter = next(
            (m for m in market["filters"] if m["filterType"] == "MIN_NOTIONAL"), None
        )
        return min_notional_filter[min_notional_limit]


class Assets(Account, Conversion):
    def __init__(self, app=None):
        self.usd_balance = 0
        self.app = app
        return super().__init__()

    def get_usd_balance(self):
        """
        Cronjob that stores balances with its approximate current value in BTC
        """
        balances = self.get_balances().json
        current_time = datetime.now()
        total_usd = 0
        for b in balances:

            # Ordinary coins found in balance
            price = self.get_conversion(current_time, b["asset"])
            usd = b["free"] * float(price)
            total_usd += usd

        return proper_round(total_usd, 8)

    def get_pnl(self):
        current_time = datetime.now()
        days = 7
        if "days" in request.args:
            days = int(request.args["days"])

        start = current_time - timedelta(days=days)
        dummy_id = ObjectId.from_datetime(start)
        data = list(
            app.db.balances.find(
                {
                    "_id": {
                        "$gte": dummy_id,
                    }
                }
            )
        )
        resp = jsonResp({"data": data}, 200)
        return resp

    def store_balance(self):
        """
        Alternative PnL data that runs as a cronjob everyday once at 1200
        Store current balance in Db
        """
        print("Store balance starting...")
        balances = self.get_balances().json
        current_time = datetime.utcnow()
        total_btc = 0
        rate = 0
        for b in balances:
            if b["asset"] != "BTC":
                # Only tether coins for hedging
                if "USD" in b["asset"]:
                    rate = self.get_ticker_price("BTC" + b["asset"])
                    btc_value = float(qty) / float(rate)
                else:
                    symbol = self.find_market(b["asset"])
                    market = self.find_quoteAsset(symbol)
                    rate = self.get_ticker_price(symbol)

                    if "locked" in b:
                        qty = b["free"] + b["locked"]
                    else:
                        qty = b["free"]

                    btc_value = float(qty) * float(rate)

                    # Non-btc markets
                    if market != "BTC":
                        x_rate = self.get_ticker_price(market + "BTC")
                        x_value = float(qty) * float(rate)
                        btc_value = float(x_value) * float(x_rate)
            else:
                if "locked" in b:
                    btc_value = b["free"] + b["locked"]
                else:
                    btc_value = b["free"]

            total_btc += btc_value

        total_usd = self.get_conversion(current_time, "BTC", "USD")
        balance = {
            "time": current_time.strftime("%Y-%m-%d"),
            "estimated_total_btc": total_btc,
            "estimated_total_usd": total_usd,
        }
        balanceId = self.app.db.balances.insert_one(
            balance, {"$currentDate": {"createdAt": "true"}}
        )
        if balanceId:
            print(f"{current_time} Balance stored!")
        else:
            print(f"{current_time} Unable to store balance! Error: {balanceId}")

    def get_value(self):
        resp = jsonResp({"message": "No balance found"}, 200)
        interval = request.view_args["interval"]
        filter = {}

        # last 24 hours
        if interval == "1d":
            filter = {
                "updatedTime": {
                    "$lt": datetime.now().timestamp(),
                    "$gte": (datetime.now() - timedelta(days=1)).timestamp(),
                }
            }

        balance = list(app.db.assets.find(filter).sort([("_id", -1)]))
        if balance:
            resp = jsonResp({"data": balance}, 200)
        return resp
