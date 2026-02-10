class LongDeal(KucoinBaseBalance):
    """
    Position manager for long futures bots.
    """

    def __init__(self, bot, db_table):
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        self.kucoin_api = KucoinFuturesApi()