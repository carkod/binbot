import json
from datetime import datetime, timedelta

import pandas as pd
from account.schemas import BalanceSchema
from bson.objectid import ObjectId
from charts.models import CandlestickParams
from charts.models import Candlestick
from db import setup_db
from tools.handle_error import json_response, json_response_error, json_response_message
from tools.round_numbers import round_numbers, round_numbers_ceiling, supress_notation
from tools.exceptions import BinanceErrors, InvalidSymbol
from deals.base import BaseDeal

class Assets(BaseDeal):
    def __init__(self):
        self.db = setup_db()
        self.usd_balance = 0
        self.isolated_balance = None

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
        total_usdt: float = 0
        rate: float = 0
        for b in bin_balance["data"]:
            # Only tether coins for hedging
            if b["asset"] == "NFT":
                continue
            elif b["asset"] in ["USD", "USDT"]:
                qty = self._check_locked(b)
                total_usdt += qty
            else:
                try:
                    qty = self._check_locked(b)
                    rate = self.get_ticker_price(f'{b["asset"]}USDT')
                    total_usdt += float(qty) * float(rate)
                except InvalidSymbol:
                    print(b["asset"])
                    # Some coins like NFT are air dropped and cannot be traded
                    break

        isolated_balance_total = self.get_isolated_balance_total()
        rate = self.get_ticker_price("BTCUSDT")
        total_usdt += float(isolated_balance_total) * float(rate)

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
        # Isolated m
        isolated_margin = self.signed_request(url=self.isolated_account_url)
        get_usdt_btc_rate = self.ticker(symbol=f"BTC{fiat}", json=False)
        total_isolated_margin = float(isolated_margin["totalNetAssetOfBtc"]) * float(
            get_usdt_btc_rate["price"]
        )

        balances = json.loads(balances_response.body)
        total_fiat = 0
        rate = 0
        left_to_allocate = 0
        for b in balances["data"]:
            # Transform tethers/stablecoins
            if "USD" in b["asset"] or fiat == b["asset"]:
                if fiat == b["asset"]:
                    left_to_allocate = b["free"]
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
            "total_fiat": total_fiat + total_isolated_margin,
            "total_isolated_margin": total_isolated_margin,
            "fiat_left": left_to_allocate,
            "asset": fiat,
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

    def match_series_dates(
        self, dates, balance_date, i: int = 0
    ) -> int | None:
        if i == len(dates):
            return None


        for idx, d in enumerate(dates):
            dt_obj = datetime.fromtimestamp(d / 1000)
            str_date = datetime.strftime(dt_obj, "%Y-%m-%d")
            
            # Match balance store dates with btc price dates
            if str_date == balance_date:
                return idx
        else:
            print("Not able to match any BTC dates for this balance store date")
            return None

    async def get_balance_series(self, end_date, start_date):
        params = {}

        if start_date:
            start_date = start_date * 1000
            try:
                float(start_date)
            except ValueError:
                resp = json_response(
                    {"message": f"start_date must be a timestamp float", "data": []}
                )
                return resp

            obj_start_date = datetime.fromtimestamp(int(float(start_date) / 1000))
            gte_tp_id = ObjectId.from_datetime(obj_start_date)
            try:
                params["_id"]["$gte"] = gte_tp_id
            except KeyError:
                params["_id"] = {"$gte": gte_tp_id}

        if end_date:
            end_date = end_date * 1000
            try:
                float(end_date)
            except ValueError as e:
                resp = json_response(
                    {"message": f"end_date must be a timestamp float: {e}", "data": []}
                )
                return resp

            obj_end_date = datetime.fromtimestamp(int(float(end_date) / 1000))
            lte_tp_id = ObjectId.from_datetime(obj_end_date)
            params["_id"]["$lte"] = lte_tp_id

        balance_series = list(self.db.balances.find(params).sort([("time", -1)]))

        # btc candlestick data series
        params = CandlestickParams(
            limit=31, # One month - 1 (calculating percentages) worth of data to display
            symbol="BTCUSDT",
            interval="1d",
        )

        cs = Candlestick()
        df, dates = cs.get_klines(params)
        trace = cs.candlestick_trace(df, dates)

        balances_series_diff = []
        balances_series_dates = []
        balance_btc_diff = []

        for index, item in enumerate(balance_series):
            btc_index = self.match_series_dates(dates, item["time"], index)
            if btc_index:
                balances_series_diff.append(float(balance_series[index]["estimated_total_usdt"]))
                balances_series_dates.append(item["time"])
                balance_btc_diff.append(float(trace["close"][btc_index]))
            else:
                continue

        resp = json_response(
            {
                "message": "Sucessfully rendered benchmark data.",
                "data": {
                    "usdt": balances_series_diff,
                    "btc": balance_btc_diff,
                    "dates": balances_series_dates,
                },
                "error": 0,
            }
        )
        return resp

    async def clean_balance_assets(self):
        """
        Check if there are many small assets (0.000.. BTC)
        if there are more than 5 (number of bots)
        transfer to BNB
        """
        data = self.signed_request(url=self.account_url)
        assets = []
        for item in data["balances"]:
            if item["asset"] not in ["USDT", "NFT", "BNB"] and float(item["free"]) > 0:
                assets.append(item["asset"])

        if len(assets) > 5:
            self.transfer_dust(assets)
            resp = json_response_message("Sucessfully cleaned balance.")
        else:
            resp = json_response_error("Amount of assets in balance is low. Transfer not needed.")

        return resp

    async def disable_isolated_accounts(self, symbol=None):
        """
        Check and disable isolated accounts
        """
        info = self.signed_request(url=self.isolated_account_url, payload={})
        for item in info["assets"]:
            # Liquidate price = 0 guarantees there is no loan unpaid
            if float(item["liquidatePrice"]) == 0:
                if float(item["baseAsset"]["free"]) > 0:
                    self.transfer_isolated_margin_to_spot(asset=item["baseAsset"]["asset"], symbol=item["symbol"], amount=float(item["baseAsset"]["free"]))
                
                if float(item["quoteAsset"]["free"]) > 0:
                    self.transfer_isolated_margin_to_spot(asset=item["quoteAsset"]["asset"], symbol=item["symbol"], amount=float(item["quoteAsset"]["free"]))

                self.disable_isolated_margin_account(item["symbol"])
                msg = "Sucessfully finished disabling isolated margin accounts."
        else:
            msg = "Disabling isolated margin account not required yet."

        resp = json_response_message(msg)
        return resp

    def one_click_liquidation(self, pair: str):
        """
        Emulate Binance Dashboard
        One click liquidation function

        This endpoint is different than the margin_liquidation function
        in that it contains some clean up functionality in the cases
        where there are are still funds in the isolated pair
        """
        
        try:
            self.margin_liquidation(pair)
            return json_response_message(f"Successfully liquidated {pair}")
        except BinanceErrors as error:
            return json_response_error(f"Error liquidating {pair}: {error.message}")

        
