import os
from binance import AsyncClient, BinanceSocketManager

class KlinesStreaming:

    def __init__(self, app):
        self.app = app

    async def setup_client(self):
        client = await AsyncClient.create(os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"])
        socket = BinanceSocketManager(client)
        return socket

    def combine_stream_names(self, interval):
        markets = list(self.app.db.bots.distinct("pair", {"status": "active"}))
        paper_trading_bots = list(
            self.app.db.paper_trading.distinct("pair", {"status": "active"})
        )
        markets = markets + paper_trading_bots
        params = []
        for market in markets:
            params.append(f"{market.lower()}@kline_{interval}")

        return params
    
    def handle_socket_error(self, msg):
        print(msg)

    async def get_klines(self, interval):
        socket = await self.setup_client()
        params = self.combine_stream_names(interval)
        klines = socket.multiplex_socket(params)

        async with klines as k:
            try:
                while True:
                    res = await k.recv()
                    print(res)
            except Exception as error:
                print(error)
    
    async def get_user_data(self):
        socket = await self.setup_client()
        user_data = socket.user_socket()
        async with user_data as ud:
            try:
                while True:
                    res = await ud.recv()
                    print(res)
            except Exception as error:
                print(error)
    
        