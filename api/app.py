# This file is for testing SQLModel
from database.api_db import ApiDb

# Required by SQLModel to create tables
from database.models.bot_table import BotTable # noqa
from database.models.deal_table import DealTable # noqa
from database.models.order_table import ExchangeOrderTable # noqa
from database.models.user_table import UserTable # noqa


def main():

    api_db = ApiDb()
    api_db.init_db()
    api_db.init_users()
    api_db.create_dummy_bot()
    result = api_db.select_bot("BTCUSDT")
    print("Created bot", result)


if __name__ == "__main__":
    main()
