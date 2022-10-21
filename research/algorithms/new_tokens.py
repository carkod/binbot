import json
import logging
import random
import re
import string
import time
from datetime import datetime

from requests import Session, get

from telegram_bot import TelegramBot


class NewTokens:
    def __init__(self) -> None:
        self.annoucements_url = (
            "https://www.binance.com/gateway-api/v1/public/cms/article/list/query"
        )
        self.session = Session()
        self.telegram_bot = TelegramBot()
        self.last_processed_kline = {}
        if not hasattr(self.telegram_bot, "updater"):
            self.telegram_bot.run_bot()
        # self.uniswap = Uniswap(address=os.getenv("METAMAX_WALLET"), private_key=os.getenv("METAMAX_KEY"), version=2)
        self.token = None
        self.amount = None
        self.tx = 1
        self.qty = 0

    def run(self):
        """
        Calculate when a coin is new
        - coinTradeTime - less than a day
        """
        logging.info("Running new tokens check...")
        # Random functions to avoid hitting cache
        rand_page_size = random.randint(1, 200)
        letters = string.ascii_letters
        random_string = "".join(
            random.choice(letters) for i in range(random.randint(10, 20))
        )
        random_number = random.randint(1, 99999999999999999999)
        queries = [
            "type=1",
            "catalogId=48",
            "pageNo=1",
            f"pageSize={str(rand_page_size)}",
            f"rnd={str(time.time())}",
            f"{random_string}={str(random_number)}",
        ]
        random.shuffle(queries)
        request_url = (
            f"{self.annoucements_url}"
            f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
        )
        response = self.session.get(request_url)
        response.raise_for_status()
        latest_announcement = response.json()
        data = latest_announcement["data"]["catalogs"][0]["articles"][0]["title"]
        tokens = re.findall("\(([^)]+)", data)

        if len(tokens) > 0:
            for i, t in enumerate(tokens):
                if (
                    t in self.last_processed_kline
                    and (float(time.time()) - float(self.last_processed_kline[t]))
                    > 86400
                ):
                    del self.last_processed_kline[t]

                get_date = latest_announcement["data"]["catalogs"][0]["articles"][i]["releaseDate"]
                dt_object = datetime.fromtimestamp(int(get_date / 1000))
                release_date = dt_object.strftime("%Y-%m-%dT%H:%M")

                # launched already?
                if datetime.now() < dt_object:
                    msg = f"New token/cryptocurrency <strong>#{t}</strong> about to launch {release_date}."
                    self.telegram_bot.send_msg(msg)
                    print(msg)
                    pass

        pass
