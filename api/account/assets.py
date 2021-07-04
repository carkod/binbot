from flask import current_app as app, request
from api.tools.jsonresp import jsonResp
from api.tools.round_numbers import proper_round
from api.tools.ticker import Conversion
from api.account.account import Account
from datetime import datetime, timedelta
from bson.objectid import ObjectId


class Assets(Account, Conversion):

    def __init__(self, app=None):
        self.usd_balance = 0
        self.app = app
        # return super(Account, self).__init__()

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
        print("Store balance starting...")
        balances = self.get_raw_balance().json
        current_time = datetime.utcnow()
        total_gbp = 0
        total_btc = 0
        rate = 0
        for b in balances:
            # Only tether coins for hedging
            if "USD" in b["asset"]:

                qty = self._check_locked(b)
                rate = self.get_conversion(current_time, "BTC", "GBP")
                total_gbp += float(qty) / float(rate)
            elif "GBP" in b["asset"]:
                total_gbp += self._check_locked(b)
            else:
                # BTC and ALT markets
                symbol = self.find_market(b["asset"])
                market = self.find_quoteAsset(symbol)
                rate = self.get_ticker_price(symbol)
                qty = self._check_locked(b)
                total = float(qty) * float(rate)
                gbp_rate = self.get_conversion(current_time, market, "GBP")

                total_gbp += float(total) * float(gbp_rate)

        # BTC value estimation from GBP
        gbp_btc_rate = self.get_conversion(current_time, "BTC", "GBP")
        total_btc = float(total_gbp) / float(gbp_btc_rate)

        balance = {
            "time": current_time.strftime("%Y-%m-%d"),
            "estimated_total_btc": total_btc,
            "estimated_total_gbp": total_gbp,
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
