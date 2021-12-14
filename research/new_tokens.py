from apis import BinbotApi
from datetime import datetime
from requests_html import HTMLSession

class NewTokens(BinbotApi):
    def __init__(self) -> None:
        self.session = HTMLSession()
        pass

    def parse_html(self):
        """
        Calculate when a coin is new

        - coinTradeTime - less than a day
        """
        r = self.session.get("https://www.binance.com/en/support/announcement/c-48")
        content = r.html.find("#__APP")[0].find("main")[0]
        find_header = r.html.search('New Cryptocurrency Listing')[0]
        return r

    def run(self):
        self.parse_html()
        pass
