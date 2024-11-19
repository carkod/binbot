import os
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select
from database.models.autotrade_table import AutotradeTable, TestAutotradeTable
from tools.enum_definitions import AutotradeSettingsDocument, BinanceKlineIntervals, DealType, Status, Strategy, UserRoles
from database.models import UserTable, ExchangeOrderTable, DealTable, BotTable
from alembic.config import Config
from alembic import command

# This allows testing/Github action dummy envs
db_url = f'postgresql://{os.getenv("POSTGRES_USER", "postgres")}:{os.getenv("POSTGRES_PASSWORD", "postgres")}@{os.getenv("POSTGRES_HOSTNAME", "localhost")}/{os.getenv("POSTGRES_DB", "postgres")}'
engine = create_engine(
    url=db_url,
)


def get_session():
    return Session(engine)


class ApiDb:
    def __init__(self):
        self.session: Session = get_session()
        pass

    def init_db(self):
        SQLModel.metadata.create_all(engine)
        self.run_migrations()
        self.init_users()
        self.create_dummy_bot()

    def run_migrations(self):
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    def drop_db(self):
        SQLModel.metadata.drop_all(engine)

    def init_autotrade_settings(self):
        """
        Dummy data for testing autotrade_settings table
        """
        statement = select(AutotradeTable).where(AutotradeTable.id == "settings")
        results = self.session.exec(statement)
        if results.first():
            return

        autotrade_data = AutotradeTable(
            id=AutotradeSettingsDocument.settings,
            balance_to_use="USDC",
            base_order_size=15,
            candlestick_interval=BinanceKlineIntervals.fifteen_minutes,
            max_active_autotrade_bots=1,
            max_request=500,
            stop_loss=0,
            take_profit=2.3,
            telegram_signals=True,
            trailling=True,
            trailling_deviation=0.63,
            trailling_profit=2.3,
            autotrade=True,
        )

        test_autotrade_data = TestAutotradeTable(
            id=AutotradeSettingsDocument.test_autotrade_settings,
            balance_to_use="USDC",
            base_order_size=15,
            candlestick_interval=BinanceKlineIntervals.fifteen_minutes,
            max_active_autotrade_bots=1,
            max_request=500,
            stop_loss=0,
            take_profit=2.3,
            telegram_signals=True,
            trailling=True,
            trailling_deviation=0.63,
            trailling_profit=2.3,
            autotrade=True,
        )

        self.session.add(autotrade_data)
        self.session.add(test_autotrade_data)
        self.session.commit()
        pass

    def init_users(self):
        """
        Dummy data for testing users table
        """

        statement = select(UserTable).where(UserTable.username == os.environ["USER"])
        results = self.session.exec(statement)
        if results.first():
            return

        username = os.environ["USER"]
        email = os.environ["EMAIL"]
        password = os.environ["PASSWORD"]

        user_data = UserTable(
            username=username, password=password, email=email, role=UserRoles.superuser
        )

        self.session.add(user_data)

        self.session.commit()

    def create_dummy_bot(self):
        """
        Dummy data for testing and initializing
        newborn DB
        """
        statement = select(BotTable)
        results = self.session.exec(statement)
        if results.first():
            return
        orders = [
            ExchangeOrderTable(
                id=1,
                order_type="market",
                time_in_force="GTC",
                timestamp=0,
                order_side="buy",
                pair="BTCUSDT",
                qty=0.000123,
                status="filled",
                price=1.222,
                deal_type=DealType.base_order,
                total_commission=0,
            ),
            ExchangeOrderTable(
                id=2,
                order_type="limit",
                time_in_force="GTC",
                timestamp=0,
                order_side="sell",
                pair="BTCUSDT",
                qty=0.000123,
                status="filled",
                price=1.222,
                deal_type=DealType.take_profit,
                total_commission=0,
            ),
        ]
        deal = DealTable(
            buy_price=0,
            buy_total_qty=0,
            buy_timestamp=0,
            current_price=0,
            sd=0,
            avg_buy_price=0,
            take_profit_price=0,
            sell_timestamp=0,
            sell_price=0,
            sell_qty=0,
            trailling_stop_loss_price=0,
            trailling_profit_price=0,
            stop_loss_price=0,
            trailling_profit=0,
            so_prices=0,
            post_closure_current_price=0,
            original_buy_price=0,
            short_sell_price=0,
            short_sell_qty=0,
            short_sell_timestamp=0,
            margin_short_loan_principal=0,
            margin_loan_id=0,
            hourly_interest_rate=0,
            margin_short_sell_price=0,
            margin_short_loan_interest=0,
            margin_short_buy_back_price=0,
            margin_short_sell_qty=0,
            margin_short_buy_back_timestamp=0,
            margin_short_base_order=0,
            margin_short_sell_timestamp=0,
            margin_short_loan_timestamp=0,
        )
        self.session.add(deal)
        bot = BotTable(
            pair="BTCUSDT",
            balance_size_to_use="1",
            balance_to_use=1,
            base_order_size=15,
            deal_id=deal.id,
            cooldown=0,
            logs='["Bot created"]',
            mode="manual",
            name="Dummy bot",
            orders=orders,
            status=Status.inactive,
            stop_loss=0,
            take_profit=2.3,
            trailling=True,
            trailling_deviation=0.63,
            trailling_profit=2.3,
            strategy=Strategy.long,
            short_buy_price=0,
            short_sell_price=0,
            total_commission=0,
        )
        self.session.add(bot)
        self.session.commit()
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
