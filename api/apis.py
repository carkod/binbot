import os
from requests import get

class CoinBaseApi:
    """
    Currency and Cryptocurrency conversion service
    """

    BASE = "https://api.coinbase.com/v2"
    EXG_URL = f"{BASE}/prices"

    def get_conversion(self, time, base="BTC", quote="GBP"):

        params = {
            "apikey": self.coin_api_key,
            "date": time.strftime('%Y-%m-%d'),
        }
        url = f"{self.EXG_URL}/{base}-{quote}/spot"
        data = get(url, params).json()
        rate = float(data["data"]["amount"])
        return rate

class BinanceApi:
    """
    Binance Api URLs
    """

    BASE = "https://api.binance.com"
    TICKER24 = f"{BASE}/api/v1/ticker/24hr"
    CANDLESTICK = f"{BASE}/api/v1/klines"
    TICKER_PRICE = f"{BASE}/api/v3/ticker/price"
    ACCOUNT = f"{BASE}/api/v3/account"
    EXCHANGE_INFO = f"{BASE}/api/v1/exchangeInfo"
    ORDER = f"{BASE}/api/v3/order"
    OPEN_ORDERS = f"{BASE}/api/v3/openOrders"
    ALL_ORDERS = f"{BASE}/api/v3/allOrders"
    AVERAGE_PRICE = f"{BASE}/api/v3/avgPrice"
    ORDER_BOOK = f"{BASE}/api/v3/depth"
    WAPI = f"{BASE}/api/v3/depth"
    WITHDRAW = f"{BASE}/wapi/v3/withdraw.html"
    DEPOSIT_HISTORY = f"{BASE}/wapi/v3/depositHistory.html"
    WITHDRAW_HISTORY = f"{BASE}/wapi/v3/withdrawHistory.html"
    DEPOSIT_ADDRESS = f"{BASE}/wapi/v3/depositAddress.html"
    USER_DATA_STREAM = f"{BASE}/api/v3/userDataStream"
    TRADE_FEE = f"{BASE}/sapi/v1/asset/tradeFee"
