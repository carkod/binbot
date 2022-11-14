import pandas as pd
from requests.models import HTTPError
from api.account.schemas import BalanceSchema
from api.tools.round_numbers import round_numbers, supress_notation
from decimal import Decimal

from flask import current_app, request
from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from api.account.account import Account
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from api.apis import CoinBaseApi
from api.app import create_app
from api.tools.handle_error import InvalidSymbol
from api.orders.models.book_order import Book_Order


class Assets(Account):
    def __init__(self):
        self.app = current_app
        self.usd_balance = 0
        self.coinbase_api = CoinBaseApi()

    def get_raw_balance(self, asset=None):
        """
        Unrestricted balance
        """
        if request:
            asset = request.args.get("asset")
        data = self.signed_request(url=self.account_url)
        df = pd.DataFrame(data["balances"])
        df["free"] = pd.to_numeric(df["free"])
        df["locked"] = pd.to_numeric(df["locked"])
        df["asset"] = df["asset"].astype(str)
        # Get table with > 0
        balances = df[(df["free"] > 0) | (df["locked"] > 0)].to_dict("records")

        if asset:
            balances = df[
                ((df["free"] > 0) | (df["locked"] > 0)) & (df["asset"] == asset)
            ].to_dict("records")
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
        bin_balance = self.get_raw_balance().json
        current_time = datetime.utcnow()
        total_usdt = 0
        rate = 0
        for b in bin_balance["data"]:
            # Only tether coins for hedging
            if b["asset"] == "NFT":
                break
            elif b["asset"] in ["USD", "USDT"]:
                qty = self._check_locked(b)
                total_usdt += qty
            else:
                try:
                    qty = self._check_locked(b)
                    rate = self.get_ticker_price(f'{b["asset"]}USDT')
                    total_usdt += float(qty) * float(rate)
                except InvalidSymbol:
                    print(InvalidSymbol(b["asset"]))
                    # Some coins like NFT are air dropped and cannot be traded
                    break

        total_balance = {
            "time": current_time.strftime("%Y-%m-%d"),
            "balances": bin_balance["data"],
            "estimated_total_usdt": round_numbers(total_usdt)
        }

        try:
            balance_schema = BalanceSchema()
            balances = balance_schema.validate_model(total_balance)
            app.db.balances.update_one(
                {"time": current_time.strftime("%Y-%m-%d")},
                {"$set": balances},
                upsert=True
            )
        except Exception as error:
            print(f"Failed to store balance: {error}")

        print("Successfully stored balance!")

    def get_value(self):
        try:
            interval = request.view_args["interval"]
        except KeyError:
            interval = None
            filter = None

        limit = request.args.get("limit", 100)
        offset = request.args.get("offset", 0)

        # last 24 hours
        if interval == "1d":
            filter = {
                "updatedTime": {
                    "$lt": datetime.now().timestamp(),
                    "$gte": (datetime.now() - timedelta(days=1)).timestamp(),
                }
            }

        balance = list(
            self.app.db.balances.find(filter)
            .sort([("_id", -1)])
            .limit(limit)
            .skip(offset)
        )
        if balance:
            resp = jsonResp({"data": balance})
        else:
            resp = jsonResp({"data": [], "error": 1})
        return resp

    def balance_estimate(self, fiat="USDT"):
        """
        Estimated balance in given fiat coin
        """
        balances = self.get_raw_balance().json
        total_fiat = 0
        rate = 0
        for b in balances["data"]:
            # Transform tethers/stablecoins
            if "USD" in b["asset"] or fiat == b["asset"]:
                total_fiat += self._check_locked(b)
            # Transform market assets/alt coins
            elif b["asset"] == "NFT":
                continue
            else:
                qty = self._check_locked(b)
                try:
                    rate = self.get_ticker_price(f'{b["asset"]}{fiat}')
                except InvalidSymbol:
                    print(f"Invalid symbol {b['asset'] + fiat}")
                total_fiat += float(qty) * float(rate)

        balance = {
            "balances": balances["data"],
            "total_fiat": total_fiat,
        }
        if balance:
            resp = jsonResp({"data": balance})
        else:
            resp = jsonResp({"data": [], "error": 1})
        return resp

    def balance_estimate_legacy(self, fiat="USDT"):
        """
        Old legacy code of balance_estimate
        """
        balances = self.get_raw_balance().json
        total_fiat = 0
        rate = 0
        for b in balances["data"]:
            # Transform tethers/stablecoins
            if "USD" in b["asset"]:
                qty = self._check_locked(b)
                rate = self.get_ticker_price(f'{fiat}{b["asset"]}')
                total_fiat += float(qty) * float(rate)
            # Transform market assets/alt coins
            elif b["asset"] in ["BTC", "BNB", "ETH", "XRP"]:
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

                # Fix binance incorrect market data for MBLBTC
                # Binance does not list MBLBTC, but the API does provide ticker_price
                # But this ticker price does not make sense, it's even lower than BNB value
                # Therefore replace with BNB market price data
                if symbol == "MBLBTC":
                    symbol = "MBLBNB"

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

    def store_balance_snapshot(self):
        """
        Alternative to storing balance,
        use Binance new snapshot endpoint to store
        Because this is a cronjob, it doesn't have application context
        """
        app = create_app()
        print("Store account snapshot starting...")
        current_time = datetime.utcnow()
        data = self.signed_request(self.account_snapshot_url, payload={"type": "SPOT"})
        spot_data = next(
            (item for item in data["snapshotVos"] if item["type"] == "spot"), None
        )
        balances = [
            balance
            for balance in spot_data["data"]["balances"]
            if (balance["free"] != "0" or balance["locked"] != "0")
        ]
        total_btc = spot_data["data"]["totalAssetOfBtc"]
        fiat_rate = self.get_ticker_price("BTCGBP")
        total_usdt = float(total_btc) * float(fiat_rate)
        balanceId = app.db.balances.insert_one(
            {
                "_id": spot_data["updateTime"],
                "time": datetime.fromtimestamp(
                    spot_data["updateTime"] / 1000.0
                ).strftime("%Y-%m-%d"),
                "balances": balances,
                "estimated_total_btc": total_btc,
                "estimated_total_usdt": total_usdt,
            }
        )
        if balanceId:
            print(f"{current_time} Balance stored!")
        else:
            print(f"{current_time} Unable to store balance! Error: {balanceId}")

    def buy_gbp_balance(self):
        """
        To buy GBP e.g.:
        - BNBGBP market sell BNB with GBP

        Sell whatever is in the balance e.g. Sell all BNB
        Always triggered after order completion
        @returns json object
        """
        try:
            asset = request.view_args["asset"].upper()
        except KeyError:
            return jsonResp_error_message("Parameter asset is required. E.g. BNB, BTC")

        new_pair = f"{asset}GBP"

        try:
            self.find_quoteAsset(f"{asset}GBP")
        except HTTPError as e:
            if e["code"] == -1121:
                return jsonResp_error_message(f"{asset} cannot be traded with GBP")

        balances = self.get_raw_balance(asset).json
        try:
            qty = float(balances["data"][0]["free"])
            if not qty or float(qty) == 0.00:
                return jsonResp_error_message(f"Not enough {asset} balance to buy GBP")
        except KeyError:
            return jsonResp_error_message(f"Not enough {asset} balance to buy GBP")

        book_order = Book_Order(new_pair)
        price = float(book_order.matching_engine(False, qty))
        # Precision for balance conversion, not for the deal
        qty_precision = -(
            Decimal(str(self.lot_size_by_symbol(new_pair, "stepSize")))
            .as_tuple()
            .exponent
        )
        price_precision = -(
            Decimal(str(self.price_filter_by_symbol(new_pair, "tickSize")))
            .as_tuple()
            .exponent
        )
        qty = round_numbers(
            float(qty),
            qty_precision,
        )

        if price:
            order = {
                "pair": new_pair,
                "qty": qty,
                "price": supress_notation(price, price_precision),
            }
            res = self.bb_request(
                method="POST", url=self.bb_buy_order_url, payload=order
            )
        else:
            # Matching engine failed - market order
            order = {
                "pair": new_pair,
                "qty": qty,
            }
            res = self.bb_request(
                method="POST", url=self.bb_sell_market_order_url, payload=order
            )

        # If error pass it up to parent function, can't continue
        if "error" in res:
            return jsonResp_error_message(res["error"])

        return jsonResp_message("Successfully bought GBP!")
