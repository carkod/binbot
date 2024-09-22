from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fastapi.responses import JSONResponse
from account.controller import AssetsController
from tools.handle_error import json_response, json_response_error, json_response_message
from tools.round_numbers import round_numbers
from tools.exceptions import BinanceErrors, InvalidSymbol, LowBalanceCleanupError, MarginLoanNotFound
from tools.enum_definitions import Status

class Assets(AssetsController):
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
        Alternative PnL data that runs as a cronjob everyday once at 12:00.
        This works outside of context.

        Stores current balance in DB and estimated
        total balance in fiat (USDC) for the day.

        Better than deprecated store_balance_snapshot
        - it doesn't required high weight
        - it can be tweaked to have our needed format
        - the result of total_usdc is pretty much the same, the difference is in 0.001 USDC
        - however we don't need a loop and we decreased one network request (also added one, because we still need the raw_balance to display charts)
        """
        fiat = self.get_fiat_coin()
        wallet_balance = self.get_wallet_balance()
        itemized_balance = self.get_raw_balance()

        rate = self.get_ticker_price(f'BTC{fiat}')

        total_wallet_balance = 0
        for item in wallet_balance:
            if item["balance"] and float(item["balance"]) > 0:
                total_wallet_balance += float(item["balance"])

        total_usdc = total_wallet_balance * float(rate)
        response  = self.create_balance_series(itemized_balance, round_numbers(total_usdc, 4))
        return response


    def balance_estimate(self):
        """
        Estimated balance in given fiat coin
        """
        fiat = self.get_fiat_coin()
        balances = self.get_raw_balance()
        total_fiat = 0
        left_to_allocate = 0
        total_isolated_margin = 0
        btc_rate = self.get_ticker_price(f'BTC{fiat}')
        wallet_balance = self.get_wallet_balance()
        for item in wallet_balance:
            if item["walletName"] == "Spot":
                total_fiat += float(item["balance"]) * float(btc_rate)
            if item["walletName"] == "Isolated Margin":
                total_isolated_margin += float(item["balance"]) * float(btc_rate)

        for b in balances:
            if b["asset"] == fiat:
                left_to_allocate = float(b["free"])
                break

        balance = {
            "balances": balances,
            "total_fiat": total_fiat + total_isolated_margin,
            "total_isolated_margin": total_isolated_margin,
            "fiat_left": left_to_allocate,
            "asset": fiat,
        }
        return balance

    def balance_series(self, fiat="USDC", start_time=None, end_time=None, limit=5):
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

    async def retrieve_gainers_losers(self, market_asset="USDC"):
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

        balance_series = self.query_balance_series(start_date, end_date)

        if len(balance_series) == 0:
            return json_response_error("No balance series data found.")

        end_time = int(datetime.strptime(balance_series[0]["time"], "%Y-%m-%d").timestamp() * 1000)
        # btc candlestick data series
        klines = self.get_raw_klines(
            limit=len(balance_series), # One month - 1 (calculating percentages) worth of data to display
            symbol="BTCUSDC",
            interval="1d",
            end_time=str(end_time),
        )

        balances_series_diff = []
        balances_series_dates = []
        balance_btc_diff = []

        for index, item in enumerate(balance_series):
            btc_index = self.consolidate_dates(klines, item["time"], index)
            if btc_index is not None:
                if "estimated_total_usdc" in balance_series[index]:
                    balances_series_diff.append(float(balance_series[index]["estimated_total_usdc"]))
                else:
                    balances_series_diff.append(float(balance_series[index]["estimated_total_usdt"]))
                balances_series_dates.append(item["time"])
                balance_btc_diff.append(float(klines[btc_index][4]))
            else:
                continue

        resp = json_response(
            {
                "message": "Sucessfully rendered benchmark data.",
                "data": {
                    "usdc": balances_series_diff,
                    "btc": balance_btc_diff,
                    "dates": balances_series_dates,
                },
                "error": 0,
            }
        )
        return resp

    def clean_balance_assets(self, bypass=False):
        """
        Check if there are many small assets (0.000.. BTC)
        if there are more than 5 (number of bots)
        transfer to BNB
        """
        data = self.get_account_balance()
        assets = []

        if len(self.exception_list) == 0:
            self.exception_list = ["USDT", "USDC", "NFT", "BNB"]

        active_bots = list(self._db.bots.find({"status": Status.active}))
        for bot in active_bots:
            quote_asset = bot["pair"].replace(bot["balance_to_use"], "")
            self.exception_list.append(quote_asset)

        for item in data["balances"]:
            if item["asset"] not in self.exception_list and float(item["free"]) > 0:
                assets.append(item["asset"])

        if len(assets) < 5 and not bypass:
            raise LowBalanceCleanupError("Amount of assets in balance is low. Transfer not needed.")
        else:
            try:
                self.transfer_dust(assets)
            except BinanceErrors as error:
                if error.code == -5005:
                    for asset in assets:
                        for string in error.message.split():
                            if asset == string:
                                self.exception_list.append(asset)
                                break
                    self.clean_balance_assets(bypass=bypass)
                    pass

        return assets

    def get_total_fiat(self, fiat="USDC"):
        """
        Simplified version of balance_estimate

        Returns:
            float: total BTC estimated in the SPOT wallet
            then converted into USDC
        """
        fiat = self.get_fiat_coin()
        wallet_balance = self.get_wallet_balance()
        get_usdc_btc_rate = self.ticker(symbol=f"BTC{fiat}", json=False)
        total_balance = 0
        rate = float(get_usdc_btc_rate["price"])
        for item in wallet_balance:
            if item["activate"]:
                total_balance += float(item["balance"])

        total_fiat = total_balance * rate
        return total_fiat

    def get_available_fiat(self, fiat="USDC"):
        """
        Simplified version of balance_estimate
        to get free/avaliable USDC.

        Getting the total USDC directly
        from the balances because if it were e.g.
        Margin trading, it would not be available for use.
        The only available fiat is the unused USDC in the SPOT wallet.

        Balance not used in Margin trading should be
        transferred back to the SPOT wallet.

        Returns:
            str: total USDC available to 
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

    def one_click_liquidation(self, pair: str) -> JSONResponse:
        """
        Emulate Binance Dashboard
        One click liquidation function

        This endpoint is different than the margin_liquidation function
        in that it contains some clean up functionality in the cases
        where there are are still funds in the isolated pair
        """

        try:
            self.margin_liquidation(pair, self.qty_precision(pair))
            return json_response_message(f"Successfully liquidated {pair}")
        except MarginLoanNotFound as error:
            return json_response_message(f"{error}. Successfully cleared isolated pair {pair}")
        except BinanceErrors as error:
            return json_response_error(f"Error liquidating {pair}: {error.message}")

    def store_market_domination(self):
        get_ticker_data = self.ticker_24()
        all_coins = []
        for item in get_ticker_data:
             if item["symbol"].endswith("USDC"):
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
