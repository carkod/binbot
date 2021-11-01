import pandas as pd
from api.tools.round_numbers import round_numbers
from decimal import Decimal

from flask import current_app, request
from api.tools.handle_error import jsonResp
from api.account.account import Account
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from api.apis import CoinBaseApi
from api.app import create_app
from api.tools.handle_error import InvalidSymbol


class Assets(Account):
    def __init__(self):
        self.app = current_app
        self.usd_balance = 0
        self.coinbase_api = CoinBaseApi()

    def get_raw_balance(self):
        """
        Unrestricted balance
        """
        data = self.signed_request(url=self.account_url)
        df = pd.DataFrame(data["balances"])
        df["free"] = pd.to_numeric(df["free"])
        df["locked"] = pd.to_numeric(df["locked"])
        df["asset"] = df["asset"].astype(str)
        # Get table with > 0
        balances = df[(df["free"] > 0) | (df["locked"] > 0)].to_dict("records")

        # filter out empty
        # Return response
        resp = jsonResp({"data": balances})
        return resp

    def get_binbot_balance(self):
        """
        More strict balance
        - No locked
        - Minus safety orders
        """
        # Get a list of safety orders
        so_list = list(
            self.app.db.bots.aggregate(
                [
                    {
                        "$addFields": {
                            "so_num": {"$size": {"$objectToArray": "$safety_orders"}},
                        }
                    },
                    {"$match": {"so_num": {"$ne": 0}}},
                    {"$addFields": {"s_os": {"$objectToArray": "$safety_orders"}}},
                    {"$unwind": "$safety_orders"},
                    {"$group": {"_id": {"so": "$s_os.v.so_size", "pair": "$pair"}}},
                ]
            )
        )
        data = self.request_data()["balances"]
        df = pd.DataFrame(data)
        df["free"] = pd.to_numeric(df["free"])
        df["asset"] = df["asset"].astype(str)
        df.drop("locked", axis=1, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # Get table with > 0
        balances = df[df["free"] > 0].to_dict("records")

        # Include safety orders
        for b in balances:
            for item in so_list:
                if b["asset"] in item["_id"]["pair"]:
                    decimals = -(
                        Decimal(
                            self.price_filter_by_symbol(item["_id"]["pair"], "tickSize")
                        )
                        .as_tuple()
                        .exponent
                    )
                    total_so = sum(
                        [float(x) if x != "" else 0 for x in item["_id"]["so"]]
                    )
                    b["free"] = round_numbers(float(b["free"]) - total_so, decimals)

        # filter out empty
        # Return response
        resp = jsonResp(balances)
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
        resp = jsonResp(data)
        return resp

    def get_pnl(self):
        current_time = datetime.now()
        days = 7
        if "days" in request.args:
            days = int(request.args["days"])

        start = current_time - timedelta(days=days)
        dummy_id = ObjectId.from_datetime(start)
        data = list(
            self.app.db.balances.find(
                {
                    "_id": {
                        "$gte": dummy_id,
                    }
                }
            )
        )
        resp = jsonResp({"data": data})
        return resp

    def _check_locked(self, b):
        qty = 0
        if "locked" in b:
            qty = b["free"] + b["locked"]
        else:
            qty = b["free"]
        return qty

    def store_balance(self):
        """
        Alternative PnL data that runs as a cronjob everyday once at 1200
        Store current balance in Db
        """
        # Store balance works outside of context as cronjob
        app = create_app()
        print("Store balance starting...")
        balances = self.get_raw_balance().json
        current_time = datetime.utcnow()
        total_gbp = 0
        total_btc = 0
        rate = 0
        for b in balances["data"]:
            print(f"Balance: {b['asset']}")
            # Only tether coins for hedging
            if b["asset"] in ["USD", "BTC", "BNB", "ETH", "XRP"]:
                qty = self._check_locked(b)
                rate = self.get_ticker_price(f'{b["asset"]}GBP')
                total_gbp += float(qty) * float(rate)
            elif "GBP" in b["asset"]:
                total_gbp += self._check_locked(b)
            else:
                try:
                    # BTC and ALT markets
                    symbol = self.find_market(b["asset"])
                except InvalidSymbol:
                    print(InvalidSymbol(b["asset"]))
                    # Some coins like NFT are air dropped and cannot be traded
                    break
                market = self.find_quoteAsset(symbol)
                rate = self.get_ticker_price(symbol)
                qty = self._check_locked(b)
                total = float(qty) * float(rate)
                if market == "BNB":
                    gbp_rate = self.get_ticker_price("BNBGBP")
                else:
                    gbp_rate = self.coinbase_api.get_conversion(
                        current_time, market, "GBP"
                    )

                total_gbp += float(total) * float(gbp_rate)

        # BTC value estimation from GBP
        gbp_btc_rate = self.get_ticker_price("BTCGBP")
        total_btc = float(total_gbp) / float(gbp_btc_rate)

        balance = {
            "time": current_time.strftime("%Y-%m-%d"),
            "balances": balances,
            "estimated_total_btc": total_btc,
            "estimated_total_gbp": total_gbp,
        }
        balanceId = app.db.balances.insert_one(
            balance, {"$currentDate": {"createdAt": "true"}}
        )
        if balanceId:
            print(f"{current_time} Balance stored!")
        else:
            print(f"{current_time} Unable to store balance! Error: {balanceId}")

    def get_value(self):
        try:
            interval = request.view_args["interval"]
        except KeyError:
            interval = None
            filter = None

        # last 24 hours
        if interval == "1d":
            filter = {
                "updatedTime": {
                    "$lt": datetime.now().timestamp(),
                    "$gte": (datetime.now() - timedelta(days=1)).timestamp(),
                }
            }

        balance = list(self.app.db.balances.find(filter).sort([("_id", -1)]))
        if balance:
            resp = jsonResp({"data": balance})
        else:
            resp = jsonResp({"data": [], "error": 1})
        return resp

    def balance_estimate(self, fiat="GBP"):
        """
        Estimated balance in given fiat coin
        """
        balances = self.get_raw_balance().json
        total_fiat = 0
        rate = 0
        for b in balances["data"]:
            # Only tether coins for hedging
            if b["asset"] in ["USD", "BTC", "BNB", "ETH", "XRP"]:
                qty = self._check_locked(b)
                rate = self.get_ticker_price(f'{b["asset"]}{fiat}')
                total_fiat += float(qty) * float(rate)
            elif fiat == b["asset"]:
                total_fiat += self._check_locked(b)
            else:
                # BTC and ALT markets
                symbol = self.find_market(b["asset"])
                if not symbol:
                    continue
                market = self.find_quoteAsset(symbol)
                rate = self.get_ticker_price(symbol)
                qty = self._check_locked(b)
                total = float(qty) * float(rate)
                fiat_rate = self.get_ticker_price(f"{market}{fiat}")
                total_fiat += float(total) * float(fiat_rate)

        balance = {
            "balances": balances["data"],
            "total_fiat": total_fiat,
        }
        if balance:
            resp = jsonResp({"data": balance})
        else:
            resp = jsonResp({"data": [], "error": 1})
        return resp

    def balance_series(self, fiat="GBP", start_time=None, end_time=None, limit=5):
        """
        Get series for graph.

        This endpoint uses high weight: 2400
        it will be easily flagged by binance
        """

        snapshot_account_data = self.signed_request(
            url=self.account_snapshot_url, payload={"type": "SPOT"}
        )
        balances = []
        for datapoint in snapshot_account_data["snapshotVos"]:

            fiat_rate = self.get_ticker_price(f"BTC{fiat}")
            total_fiat = float(datapoint["data"]["totalAssetOfBtc"]) * float(fiat_rate)
            balance = {
                "update_time": datapoint["updateTime"],
                "balances": datapoint["data"]["balances"],
                "total_btc": datapoint["data"]["totalAssetOfBtc"],
                "total_fiat": total_fiat,
            }
            balances.append(balance)

        if balance:
            resp = jsonResp({"data": balances})
        else:
            resp = jsonResp({"data": [], "error": 1})
        return resp

    def currency_conversion(self):
        base = request.args.get("base")
        quote = request.args.get("quote")
        qty = request.args.get("qty")

        # Get conversion from coinbase
        time = datetime.now()
        rate = self.coinbase_api.get_conversion(time, base, quote)
        total = float(rate) * float(qty)
        return jsonResp({"data": total})
