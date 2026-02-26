from apscheduler.schedulers.blocking import BlockingScheduler
from account.controller import ConsolidatedAccounts
from exchange_apis.binance.assets import Assets
from databases.symbols_etl import SymbolDataEtl
from charts.controllers import MarketDominationController
from databases.utils import independent_session
from pybinbot import ExchangeId, configure_logging
from tools.config import Config


def main():
    config = Config()
    configure_logging(force=True)
    scheduler = BlockingScheduler()
    assets = Assets(session=independent_session())
    consolidated_accounts = ConsolidatedAccounts(session=independent_session())
    market_domination = MarketDominationController()
    symbols_crud = SymbolDataEtl(session=independent_session())

    autotrade_settings = assets.autotrade_settings
    exchange = ExchangeId(autotrade_settings.exchange_id)

    # Jobs should be distributed as far as possible from each other
    # to avoid overloading RAM and also avoid hitting rate limits due to high weight
    # that's why they are placed at midnight
    scheduler.add_job(
        func=symbols_crud.etl_symbols_updates,
        trigger="cron",
        timezone=config.timezone,
        day_of_week="sat",
        hour=11,
        minute=0,
        id="update_symbols",
    )
    scheduler.add_job(
        func=consolidated_accounts.store_balance,
        trigger="cron",
        timezone=config.timezone,
        hour=1,
        minute=1,
        id="store_balance",
    )
    if exchange == ExchangeId.BINANCE:
        scheduler.add_job(
            func=assets.disable_isolated_accounts,
            trigger="cron",
            timezone=config.timezone,
            hour=2,
            minute=1,
            id="disable_isolated_accounts",
        )
        scheduler.add_job(
            func=consolidated_accounts.clean_balance_assets,
            trigger="cron",
            timezone=config.timezone,
            hour=3,
            minute=27,
            id="clean_balance_assets",
        )
    scheduler.add_job(
        func=market_domination.ingest_adp_data,
        trigger="interval",
        timezone=config.timezone,
        hours=1,
        id="ingest_adp_data",
    )
    scheduler.start()


if __name__ == "__main__":
    main()
