import json
from datetime import datetime, timedelta

import pandas as pd
from account.account import Account
from account.schemas import BalanceSchema
from bson.objectid import ObjectId
from db import setup_db
from tools.handle_error import InvalidSymbol, json_response, json_response_message
from tools.round_numbers import round_numbers


class Assets(Account):
    def __init__(self):
        self.db = setup_db()
        self.usd_balance = 0

    def get_raw_balance(self, asset=None):
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

        if asset:
            balances = df[
                ((df["free"] > 0) | (df["locked"] > 0)) & (df["asset"] == asset)
            ].to_dict("records")
        # filter out empty
        # Return response
        resp = json_response({"data": balances})
        return resp

    def get_pnl(self, days=7):
        current_time = datetime.now()
        start = current_time - timedelta(days=days)
        dummy_id = ObjectId.from_datetime(start)
        data = list(
            self.db.balances.find(
                {
                    "_id": {
                        "$gte": dummy_id,
                    }
                }
            )
        )
        resp = json_response({"data": data})
        return resp

    def _check_locked(self, b):
        qty = 0
        if "locked" in b:
            qty = b["free"] + b["locked"]
        else:
            qty = b["free"]
        return qty

    def store_balance(self) -> dict:
        """
        Alternative PnL data that runs as a cronjob everyday once at 1200
        Store current balance in Db
        """
        # Store balance works outside of context as cronjob
        balances_response = self.get_raw_balance()
        bin_balance = json.loads(balances_response.body)
        current_time = datetime.utcnow()
        total_usdt = 0
        rate: float = 0
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
                    rate: float = self.get_ticker_price(f'{b["asset"]}USDT')
                    total_usdt += float(qty) * float(rate)
                except InvalidSymbol:
                    print(b["asset"])
                    # Some coins like NFT are air dropped and cannot be traded
                    break

        total_balance = {
            "time": current_time.strftime("%Y-%m-%d"),
            "balances": bin_balance["data"],
            "estimated_total_usdt": round_numbers(total_usdt),
        }

        try:
            balance_schema = BalanceSchema(**total_balance)
            balances = balance_schema.dict()
            self.db.balances.update_one(
                {"time": current_time.strftime("%Y-%m-%d")},
                {"$set": balances},
                upsert=True,
            )
        except Exception as error:
            print(f"Failed to store balance: {error}")

        print("Successfully stored balance!")
        return json_response_message("Successfully stored balance!")

    def balance_estimate(self, fiat="USDT"):
        """
        Estimated balance in given fiat coin
        """
        balances_response = self.get_raw_balance()
        balances = json.loads(balances_response.body)
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
            resp = json_response({"data": balance})
        else:
            resp = json_response({"data": [], "error": 1})
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
            resp = json_response({"data": balances})
        else:
            resp = json_response({"data": [], "error": 1})
        return resp

    def store_balance_snapshot(self):
        """
        Alternative to storing balance,
        use Binance new snapshot endpoint to store
        with a very high rate limit weight

        Because this is a cronjob, it doesn't have application context
        """
        db = setup_db()
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
        balanceId = db.balances.insert_one(
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

    async def retrieve_gainers_losers(self, market_asset="USDT"):
        """
        Create and return a ranking with gainers vs losers data
        """
        data = self.ticker_24()
        gainers_losers_list = [
            item for item in data if item["symbol"].endswith(market_asset)
        ]
        gainers_losers_list.sort(
            reverse=True, key=lambda item: float(item["priceChangePercent"])
        )

        return json_response(
            {
                "message": "Successfully retrieved gainers and losers data",
                "data": gainers_losers_list,
            }
        )
