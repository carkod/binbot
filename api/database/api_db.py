import os
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select
from tools.enum_definitions import DealType, Status, Strategy, UserRoles
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

    def init_users(self):
        """
        Dummy data for testing users table
        """

        username = os.environ["USER"]
        email = os.environ["EMAIL"]
        password = os.environ["PASSWORD"]

        user_data = UserTable(
            username=username, password=password, email=email, role=UserRoles.superuser
        )

        self.session.add(user_data)

        self.session.commit()
        self.session.close()

    def create_dummy_bot(self):
        """
        Dummy data for testing and initializing
        newborn DB
        """
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
        self.session.close()
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
