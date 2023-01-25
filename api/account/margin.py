import os
from datetime import datetime

from binance.client import Client

from account.schemas import EstimatedBalance
from tools.handle_error import json_response


class MarginAccount:
    def __init__(self) -> None:
        self.client = Client(os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"])

    def margin_balance_estimate(self):
        info = self.client.get_margin_account()
        assets = [item for item in info["userAssets"] if float(item["netAsset"]) > 0]
        usdt_value = self.client.get_symbol_ticker(symbol="BTCUSDT")
        current_time = datetime.utcnow()
        balance = EstimatedBalance(
            time=current_time.strftime("%Y-%m-%d"),
            assets=assets,
            estimated_total_usdt=float(info["totalAssetOfBtc"])
            * float(usdt_value["price"]),
        )
        return json_response({"message": "Successfully return margin balance estimate", "data": balance.dict()})
