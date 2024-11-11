# This file is for testing SQLModel
from database.api_db import ApiDb

# Required by SQLModel to create tables
from database.models.bot_table import BotTable # noqa
from database.models.deal_table import DealTable # noqa
from database.models.order_table import ExchangeOrderTable # noqa


def main():

    api_db = ApiDb()
    api_db.create_db_and_tables()
    api_db.create_dummy_bot()


if __name__ == "__main__":
    main()
