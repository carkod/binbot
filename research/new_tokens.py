from apis import BinbotApi
from datetime import datetime

class NewTokens(BinbotApi):
    def __init__(self) -> None:
        pass
    
    def check_new_coin(self, coin_trade_time: int):
        """
        Calculate when a coin is new

        - coinTradeTime - less than a day
        """
        trade_time_diff = datetime.now() - datetime.fromtimestamp(coin_trade_time)
        return trade_time_diff.days < 1
    
    def run(self):
        projects = self.launchpool_projects()
        new_pairs = set([item["rebaseCoin"] + item["asset"] for item in projects["data"]["completed"]["list"] if self.check_new_coin(item["coinTradeTime"])])

        # Use this endpoint as it has less weight 
        ticker_price_data = self.ticker_price()
        list_current_pairs = set([item["symbol"] for item in ticker_price_data])

        list_pairs = list(new_pairs - list_current_pairs)
            
        return data 
