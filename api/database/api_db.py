import os
from sqlmodel import Session, SQLModel, create_engine
from database.models.deal_table import DealTable
from tools.enum_definitions import Status
from binquant.shared.enums import Strategy
from database.models.bot_table import BotTable


class ApiDb:
    # This allows testing/Github action dummy envs
    api_db_url = f"""
        postgresql://{os.getenv("POSTGRES_USER", "postgres")}:{os.getenv("POSTGRES_PASSWORD", "postgres")}@{os.getenv("POSTGRES_HOST", "localhost")}/{os.getenv
        ("POSTGRES_DB", "postgres")}
    """

    def __init__(self):
        self.engine = create_engine(
            self.api_db_url,
            connect_args={"check_same_thread": False},
            echo=os.getenv("DEBUG", False),
        )

    def init_db(self):
        self.create_db_and_tables()

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def create_dummy_bot(self):
        with Session(self.engine) as session:
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
            bot = BotTable(
                pair="BTCUSDT",
                balance_size_to_use="1",
                balance_to_use=1,
                base_order_size=15,
                deal_id=deal.id,
                cooldown=0,
                errors=[],
                mode="manual",
                name="Dummy bot",
                orders=[],
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
            session.add(bot)
            session.commit()
            session.refresh(bot)
            return bot
