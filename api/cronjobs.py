import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from account.assets import Assets
from charts.controllers import MarketDominationController
from database.utils import independent_session

logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
logging.basicConfig(
    level=logging.INFO,
    filename=None,
    format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    scheduler = BlockingScheduler()
    assets = Assets(session=independent_session())
    market_domination = MarketDominationController()
    timezone = "Europe/London"

    # Jobs should be distributed as far as possible from each other
    # to avoid overloading RAM and also avoid hitting rate limits due to high weight
    scheduler.add_job(
        func=assets.store_balance,
        trigger="cron",
        timezone=timezone,
        hour=1,
        minute=1,
        id="store_balance",
    )
    scheduler.add_job(
        func=assets.disable_isolated_accounts,
        trigger="cron",
        timezone=timezone,
        hour=2,
        minute=1,
        id="disable_isolated_accounts",
    )
    scheduler.add_job(
        func=assets.clean_balance_assets,
        trigger="cron",
        timezone=timezone,
        hour=3,
        minute=27,
        id="clean_balance_assets",
    )
    scheduler.add_job(
        func=market_domination.store_market_domination,
        trigger="interval",
        timezone=timezone,
        hours=2,
        id="market_domination",
    )
    scheduler.start()


if __name__ == "__main__":
    main()
