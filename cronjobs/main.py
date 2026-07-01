from apscheduler.schedulers.blocking import BlockingScheduler
from api.account.controller import ConsolidatedAccounts
from api.exchange_apis.binance.assets import Assets
from api.databases.crud.signals_crud import SignalsCrud
from api.databases.symbols_etl import SymbolDataEtl
from api.charts.controllers import MarketDominationController
from api.databases.utils import independent_session
from pybinbot import ExchangeId, configure_logging
from api.tools.config import Config
from api.web3_candidates.ingest_web3_candidates import IngestWeb3Candidates


def main():
    config = Config()
    configure_logging(force=True)
    scheduler = BlockingScheduler()
    assets = Assets(session=independent_session())
    consolidated_accounts = ConsolidatedAccounts(session=independent_session())
    market_domination = MarketDominationController()
    symbols_crud = SymbolDataEtl()
    signals_crud = SignalsCrud()
    web3_candidates_ingester = IngestWeb3Candidates(session=independent_session())

    autotrade_settings = assets.autotrade_settings
    exchange = ExchangeId(autotrade_settings.exchange_id)

    # Jobs should be distributed as far as possible from each other
    # to avoid overloading RAM and also avoid hitting rate limits due to high weight
    # that's why they are placed in off-peak windows.
    scheduler.add_job(
        func=symbols_crud.etl_symbols_ingestion,
        trigger="cron",
        timezone=config.timezone,
        day_of_week=5,
        hour=4,
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
    scheduler.add_job(
        func=signals_crud.delete_entries_older_than_14_days,
        trigger="cron",
        timezone=config.timezone,
        day_of_week=6,
        hour=1,
        minute=5,
        id="delete_old_signals",
    )
    scheduler.add_job(
        func=web3_candidates_ingester.ingest_web3_candidates,
        trigger="cron",
        timezone=config.timezone,
        hour=6,
        minute=0,
        id="ingest_web3_candidates",
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
        func=market_domination.ingest_market_breadth,
        trigger="interval",
        timezone=config.timezone,
        minutes=15,
        id="ingest_market_breadth",
    )
    scheduler.start()


if __name__ == "__main__":
    main()
