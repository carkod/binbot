from datetime import datetime, timedelta

import pandas as pd
from account.schemas import BalanceSchema, MarketDominationSeries
from bson.objectid import ObjectId
from charts.models import CandlestickParams
from charts.models import Candlestick
from db import setup_db
from tools.handle_error import json_response, json_response_error, json_response_message
from tools.round_numbers import round_numbers
from tools.exceptions import BinanceErrors, InvalidSymbol, MarginLoanNotFound
from deals.base import BaseDeal
from tools.enum_definitions import Status

class Assets(BaseDeal):
    def __init__(self):
        self.usd_balance = 0
        self.exception_list = []

    def get_raw_balance(self, asset=None):
        """
        Unrestricted balance
        """
        data = self.get_account_balance()
        balances = []
        for item in data["balances"]:
            if float(item["free"]) > 0 or float(item["locked"]) > 0:
                if asset:
                    if item["asset"] == asset:
                        balances.append(item)
                else:
                    balances.append(item)
        return balances

    def get_pnl(self, days=7):
        current_time = datetime.now()
        start = current_time - timedelta(days=days)
        dummy_id = ObjectId.from_datetime(start)
        data = list(
            self._db.balances.find(
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
            qty = float(b["free"]) + float(b["locked"])
        else:
            qty = float(b["free"])
        return qty

    def store_balance(self) -> dict:
        """
        Alternative PnL data that runs as a cronjob everyday once at 1200
        Store current balance in Db
        """
        # Store balance works outside of context as cronjob
        bin_balance = self.get_raw_balance()
        current_time = datetime.now()
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
            self._db.balances.update_one(
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
        balances = self.get_raw_balance()
        # Isolated m
        isolated_margin = self.signed_request(url=self.isolated_account_url)
        get_usdt_btc_rate = self.ticker(symbol=f"BTC{fiat}", json=False)
        total_isolated_margin = float(isolated_margin["totalNetAssetOfBtc"]) * float(
            get_usdt_btc_rate["price"]
        )

        total_fiat = 0
        rate = 0
        left_to_allocate = 0
        for b in balances:
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
            "balances": balances,
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
        current_time = datetime.now()
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

    """
    In order to create benchmark charts,
    gaps in the balances' dates need to match with BTC dates
    """
    def consolidate_dates(
        self, klines, balance_date, i: int = 0
    ) -> int | None:
        
        if i == len(klines):
            return None

        for idx, d in enumerate(klines):
            dt_obj = datetime.fromtimestamp(d[0] / 1000)
            str_date = datetime.strftime(dt_obj, "%Y-%m-%d")
            
            # Match balance store dates with btc price dates
            if str_date == balance_date:
                return idx
        else:
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

        balance_series = list(self._db.balances.find(params).sort([("time", -1)]))

        end_time = int(datetime.strptime(balance_series[0]["time"], "%Y-%m-%d").timestamp() * 1000)
        # btc candlestick data series
        klines = self.get_raw_klines(
            limit=len(balance_series), # One month - 1 (calculating percentages) worth of data to display
            symbol="BTCUSDT",
            interval="1d",
            end_time=str(end_time),
        )

        balances_series_diff = []
        balances_series_dates = []
        balance_btc_diff = []

        for index, item in enumerate(balance_series):
            btc_index = self.consolidate_dates(klines, item["time"], index)
            if btc_index is not None:
                balances_series_diff.append(float(balance_series[index]["estimated_total_usdt"]))
                balances_series_dates.append(item["time"])
                balance_btc_diff.append(float(klines[btc_index][4]))
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

    def clean_balance_assets(self):
        """
        Check if there are many small assets (0.000.. BTC)
        if there are more than 5 (number of bots)
        transfer to BNB
        """
        data = self.signed_request(url=self.account_url)
        assets = []
        resp = json_response_error("Amount of assets in balance is low. Transfer not needed.")

        if len(self.exception_list) == 0:
            self.exception_list = ["USDT", "NFT", "BNB"]

        active_bots = list(self._db.bots.find({"status": Status.active}))
        for bot in active_bots:
            quote_asset = bot["pair"].replace(bot["balance_to_use"], "")
            self.exception_list.append(quote_asset)

        for item in data["balances"]:
            if item["asset"] not in self.exception_list and float(item["free"]) > 0:
                assets.append(item["asset"])

        if len(assets) > 5:
            try:
                self.transfer_dust(assets)
                resp = json_response_message("Sucessfully cleaned balance.")
            except BinanceErrors as error:
                resp = json_response_error(f"Failed to clean balance: {error}")

        return resp

    def get_total_fiat(self, fiat="USDT"):
        """
        Simplified version of balance_estimate

        Returns:
            float: total BTC estimated in the SPOT wallet
            then converted into USDT
        """
        wallet_balance = self.get_wallet_balance()
        get_usdt_btc_rate = self.ticker(symbol=f"BTC{fiat}", json=False)
        total_balance = 0
        rate = float(get_usdt_btc_rate["price"])
        for item in wallet_balance:
            if item["activate"]:
                total_balance += float(item["balance"])

        total_fiat = total_balance * rate
        return total_fiat

    def get_available_fiat(self, fiat="USDT"):
        """
        Simplified version of balance_estimate
        to get free/avaliable USDT.

        Getting the total USDT directly
        from the balances because if it were e.g.
        Margin trading, it would not be available for use.
        The only available fiat is the unused USDT in the SPOT wallet.

        Balance not used in Margin trading should be
        transferred back to the SPOT wallet.

        Returns:
            str: total USDT available to 
        """
        total_balance = self.get_raw_balance()
        for item in total_balance:
            if item["asset"] == fiat:
                return float(item["free"])
        else:
            return 0


    def disable_isolated_accounts(self, symbol=None):
        """
        Check and disable isolated accounts
        """
        info = self.signed_request(url=self.isolated_account_url, payload={})
        msg = "Disabling isolated margin account not required yet."
        for item in info["assets"]:
            # Liquidate price = 0 guarantees there is no loan unpaid
            if float(item["liquidatePrice"]) == 0:
                if float(item["baseAsset"]["free"]) > 0:
                    self.transfer_isolated_margin_to_spot(asset=item["baseAsset"]["asset"], symbol=item["symbol"], amount=float(item["baseAsset"]["free"]))
                
                if float(item["quoteAsset"]["free"]) > 0:
                    self.transfer_isolated_margin_to_spot(asset=item["quoteAsset"]["asset"], symbol=item["symbol"], amount=float(item["quoteAsset"]["free"]))

                self.disable_isolated_margin_account(item["symbol"])
                msg = "Sucessfully finished disabling isolated margin accounts."

        return json_response_message(msg)

    def one_click_liquidation(self, pair: str):
        """
        Emulate Binance Dashboard
        One click liquidation function

        This endpoint is different than the margin_liquidation function
        in that it contains some clean up functionality in the cases
        where there are are still funds in the isolated pair
        """

        try:
            self.symbol = pair
            self.margin_liquidation(pair, self.qty_precision)
            return json_response_message(f"Successfully liquidated {pair}")
        except MarginLoanNotFound as error:
            return json_response_message(f"{error}. Successfully cleared isolated pair {pair}")
        except BinanceErrors as error:
            return json_response_error(f"Error liquidating {pair}: {error.message}")

    def store_market_domination(self):
        get_ticker_data = self.ticker_24()
        all_coins = []
        for item in get_ticker_data:
             if item["symbol"].endswith("USDT"):
                all_coins.append({
                    "symbol": item["symbol"],
                    "priceChangePercent": item["priceChangePercent"],
                    "volume": item["volume"],
                    "price": item["lastPrice"]
                })

        all_coins = sorted(all_coins, key=lambda item: float(item["priceChangePercent"]), reverse=True)
        try:
            current_time = datetime.now()
            self._db.market_domination.insert_one(
                {
                    "time": current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    "data": all_coins
                }
            )
            return json_response_message("Successfully stored market domination data.")
        except Exception as error:
            print(f"Failed to store balance: {error}")

    def get_market_domination(self, size=7):
        """
        Get gainers vs losers historical data

        Args:
            size (int, optional): Number of data points to retrieve. Defaults to 7 (1 week).
        Returns:
            dict: A dictionary containing the market domination data, including gainers and losers counts, percentages, and dates.
        """
        query = {"$query": {}, "$orderby": {"_id": -1}}
        result = self._db.market_domination.find(query).limit(size)
        return list(result)
