import logging
from charts.controllers import MarketDominationController
from databases.tables.inquiry_table import InquiryTable
from databases.symbols_etl import SymbolDataEtl
from databases.tables.autotrade_table import AutotradeTable, TestAutotradeTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable, FakeOrderTable
from databases.tables.user_table import UserTable
from databases.tables.bot_table import BotTable, PaperTradingTable
from sqlmodel import SQLModel, Session, select, text
from pybinbot import (
    AutotradeSettingsDocument,
    BinanceKlineIntervals,
    DealType,
    ExchangeId,
    Status,
    Strategy,
    OrderStatus,
    BinbotErrors,
)
from alembic import command
from alembic.script import ScriptDirectory
from alembic.config import Config
from databases.utils import engine
from exchange_apis.binance.assets import Assets
from databases.crud.symbols_crud import SymbolsCrud
from databases.crud.asset_index_crud import AssetIndexCrud
from databases.db import setup_kafka_db
from tools.config import Config as AppConfig


class ApiDb:
    """
    Initialization data for API SQL database
    """

    def __init__(self):
        self.session = Session(engine)
        self.kafka_db = setup_kafka_db()
        self.config = AppConfig()
        pass

    def init_db(self):
        self.run_migrations()
        self.init_users()
        self.init_autotrade_settings()
        self.init_test_autotrade_settings()
        self.create_dummy_bot()
        self.init_symbols()
        # Depends on autotrade settings
        self.init_balances()
        self.init_inquiries()
        self.init_market_breadth()

        logging.info("Finishing db operations")

    def init_market_breadth(self):
        controller = MarketDominationController()
        controller.migrate_adrs()
        logging.debug("Finished initializing market breadth data")

    def run_migrations(self):
        """
        Run alembic migrations to upgrade database schema.
        """
        logging.info("Running alembic migrations")
        try:
            alembic_cfg = Config("alembic.ini")
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            heads = script_dir.get_heads()

            if not heads:
                logging.warning(
                    "No Alembic heads found; skipping migration step because there is nothing to apply."
                )
                return

            head_revision = heads[0]
            versions: list[str] = []

            # Auto-heal a duplicated/branched alembic_version table if it ever happens.
            # Keep the real head revision and drop any older rows so Alembic can continue.
            try:
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                    versions = [row[0] for row in result]

                    if len(versions) > 1:
                        keep_version = None
                        for v in versions:
                            if v in heads:
                                keep_version = v
                                break

                        if keep_version is None:
                            keep_version = versions[0]
                            logging.warning(
                                "Alembic version table has multiple entries %s but none match known heads %s; "
                                "keeping %s and dropping the rest.",
                                versions,
                                heads,
                                keep_version,
                            )
                        else:
                            logging.warning(
                                "Alembic version table has multiple entries %s; keeping head %s and dropping the rest.",
                                versions,
                                keep_version,
                            )

                        conn.execute(
                            text(
                                "DELETE FROM alembic_version WHERE version_num != :keep_version"
                            ),
                            {"keep_version": keep_version},
                        )
                        conn.commit()
                        versions = [keep_version]
            except Exception as heal_exc:
                # If anything goes wrong while reading/healing, log and continue. We'll stamp if needed.
                logging.info(
                    "Unable to inspect alembic_version table (maybe it does not exist yet): %s",
                    heal_exc,
                )
                versions = []

            current_revision = versions[0] if versions else None

            if current_revision is None:
                logging.info(
                    "Database has no Alembic version; stamping to head %s without running migrations.",
                    head_revision,
                )
                command.stamp(alembic_cfg, head_revision)
                return

            if current_revision == head_revision:
                logging.info(
                    "Database already at Alembic head %s; skipping migration run.",
                    head_revision,
                )
                return

            logging.info(
                "Upgrading database from revision %s to head %s.",
                current_revision,
                head_revision,
            )
            command.upgrade(alembic_cfg, "head")
            logging.info("Alembic migrations completed successfully")
        except Exception as exc:
            logging.error(f"Alembic migrations failed: {exc}", exc_info=True)

    def delete_autotrade_settings_table(self, table_name: str):
        """
        Delete autotrade settings table
        Used for testing purposes
        """
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            conn.commit()
            SQLModel.metadata.create_all(engine)

    def init_autotrade_settings(self, delete_existing: bool = False):
        """
        Dummy data for testing autotrade_settings table
        """
        if delete_existing:
            self.delete_autotrade_settings_table("autotrade")

        statement = select(AutotradeTable).where(
            AutotradeTable.id == AutotradeSettingsDocument.settings
        )
        results = self.session.exec(statement)
        if results.first():
            return

        autotrade_data = AutotradeTable(
            id=AutotradeSettingsDocument.settings,
            fiat="USDC",
            base_order_size=20,
            candlestick_interval=BinanceKlineIntervals.fifteen_minutes,
            max_active_autotrade_bots=3,
            max_request=500,
            stop_loss=3,
            take_profit=2.3,
            telegram_signals=True,
            trailling=True,
            trailling_deviation=1.63,
            trailling_profit=2.3,
            autotrade=True,
            autoswitch=False,
            exchange_id=ExchangeId.BINANCE,
        )

        self.session.add(autotrade_data)
        pass

    def init_test_autotrade_settings(self, delete_existing: bool = False):
        if delete_existing:
            self.delete_autotrade_settings_table("test_autotrade")

        statement = select(TestAutotradeTable).where(
            TestAutotradeTable.id == AutotradeSettingsDocument.test_autotrade_settings
        )
        results = self.session.exec(statement)
        if results.first():
            return

        test_autotrade_data = TestAutotradeTable(
            id=AutotradeSettingsDocument.test_autotrade_settings,
            fiat="USDC",
            base_order_size=20,
            candlestick_interval=BinanceKlineIntervals.fifteen_minutes,
            max_active_autotrade_bots=3,
            max_request=500,
            stop_loss=3,
            take_profit=2.3,
            telegram_signals=True,
            trailling=True,
            trailling_deviation=1.63,
            trailling_profit=2.3,
            autotrade=False,
            exchange_id=ExchangeId.BINANCE,
        )
        self.session.add(test_autotrade_data)
        self.session.commit()
        pass

    def init_users(self):
        """
        Dummy data for testing users table
        """
        username = self.config.user
        email = self.config.email
        password = self.config.password
        role = self.config.role

        statement = select(UserTable).where(UserTable.username == username)
        results = self.session.exec(statement)
        if not results.first():
            user_data = UserTable(
                username=username,
                password=password,
                email=email,
                role=role,
                full_name="Admin",
            )
            self.session.add(user_data)

        service_username = self.config.service_user
        service_email = self.config.service_email
        service_password = self.config.service_password
        service_role = self.config.service_role

        result = self.session.exec(
            select(UserTable).where(UserTable.username == service_username)
        )
        if not result.first():
            service_user_data = UserTable(
                username=service_username,
                password=service_password,
                email=service_email,
                role=service_role,
                full_name="Service User",
            )
            self.session.add(service_user_data)

        self.session.commit()
        return

    def create_dummy_bot(self):
        """
        Dummy data for testing and initializing
        newborn DB
        """
        statement = select(BotTable)
        results = self.session.exec(statement)
        if results.first():
            return
        self.session.close()
        base_order = ExchangeOrderTable(
            order_id="123",
            order_type="market",
            time_in_force="GTC",
            timestamp=0,
            order_side="buy",
            pair="BTCUSDC",
            qty=0.000123,
            status=OrderStatus.FILLED,
            price=1.222,
            deal_type=DealType.base_order,
            total_commission=0,
        )
        take_profit_order = ExchangeOrderTable(
            order_id="456",
            order_type="limit",
            time_in_force="GTC",
            timestamp=0,
            order_side="sell",
            pair="BTCUSDC",
            qty=0.000123,
            status=OrderStatus.FILLED,
            price=1.222,
            deal_type=DealType.take_profit,
            total_commission=0,
        )
        deal = DealTable(
            opening_price=1.7777,
            opening_qty=12,
            opening_timestamp=0,
            current_price=0,
            sd=0,
            avg_opening_price=0,
            take_profit_price=0.02333,
            trailling_stop_loss_price=0,
            trailling_profit_price=0,
            stop_loss_price=0,
            margin_loan_id=0,
            margin_repay_id=0,
            closing_timestamp=0,
            closing_price=0,
            closing_qty=0,
        )
        bot = BotTable(
            pair="BTCUSDC",
            balance_size_to_use="1",
            fiat="USDC",
            base_order_size=15,
            deal=deal,
            cooldown=0,
            logs=["Bot created"],
            mode="manual",
            name="Dummy bot",
            orders=[base_order, take_profit_order],
            status=Status.inactive,
            stop_loss=0,
            take_profit=2.3,
            trailling=True,
            trailling_deviation=0.63,
            trailling_profit=2.3,
            strategy=Strategy.long,
            short_opening_price=0,
            short_sell_price=0,
            total_commission=0,
        )

        statement = select(PaperTradingTable)
        results = self.session.exec(statement)
        if results.first():
            return

        # Create separate fake orders for paper trading bot
        fake_base_order = FakeOrderTable(
            order_id="789",
            order_type="market",
            time_in_force="GTC",
            timestamp=0,
            order_side="buy",
            pair="BTCUSDC",
            qty=0.000123,
            status=OrderStatus.FILLED,
            price=1.222,
            deal_type=DealType.base_order,
            total_commission=0,
        )
        fake_take_profit_order = FakeOrderTable(
            order_id="990",
            order_type="limit",
            time_in_force="GTC",
            timestamp=0,
            order_side="sell",
            pair="BTCUSDC",
            qty=0.000123,
            status=OrderStatus.FILLED,
            price=1.222,
            deal_type=DealType.take_profit,
            total_commission=0,
        )

        paper_trading_bot = PaperTradingTable(
            pair="BTCUSDC",
            balance_size_to_use=1,
            fiat=1,
            base_order_size=15,
            deal=deal,
            cooldown=0,
            logs=["Paper trading bot created"],
            mode="manual",
            name="Dummy bot",
            orders=[fake_base_order, fake_take_profit_order],
            status=Status.inactive,
            stop_loss=0,
            take_profit=2.3,
            trailling=True,
            trailling_deviation=0.63,
            trailling_profit=2.3,
            strategy=Strategy.long,
            short_opening_price=0,
            short_sell_price=0,
            total_commission=0,
        )
        self.session.add(bot)
        self.session.add(paper_trading_bot)
        self.session.commit()
        self.session.refresh(bot)
        self.session.refresh(paper_trading_bot)
        return bot

    def select_bot(self, pair):
        statement = select(BotTable).where(BotTable.pair == pair)
        results = self.session.exec(statement)
        bot = results.first()
        return bot

    def delete_bot(self, pair):
        statement = select(BotTable).where(BotTable.pair == pair)
        results = self.session.exec(statement)
        self.session.delete(results.first())
        self.session.commit()
        self.session.close()
        return results.first()

    def init_symbols(self):
        """
        Heavy operation, only execute if db is empty

        First check if symbols have been updated in the last 24 hours.
        Use BNBUSDC, because db init will add BTCUSDC
        """
        self.symbols = SymbolsCrud(self.session)
        self.symbols_etl = SymbolDataEtl(self.session)
        self.asset_indexes = AssetIndexCrud(self.session)

        try:
            self.symbols.get_symbol("DASHBTC")
        except BinbotErrors:
            self.symbols_etl.etl_symbols_ingestion(delete_existing=True)

        pass

    def init_balances(self):
        statement = select(UserTable)
        results = self.session.exec(statement)
        balances = results.first()
        if balances:
            return
        assets = Assets(self.session)
        assets.store_balance()
        pass

    def init_inquiries(self):
        statement = select(InquiryTable)
        results = self.session.exec(statement)
        if not results.first():
            # No inquiries, create a dummy one
            inquiry = InquiryTable(
                full_name="John Doe",
                email="example@gmail.com",
                phone="+1234567890",
                organisation="Example Inc",
                reason="How to use the API?",
                message="I want to know how to use the API",
            )
            self.session.add(inquiry)
            self.session.commit()
            self.session.refresh(inquiry)
            logging.info(f"Created dummy inquiry with id {inquiry.id}")
        pass
