from requests import get
from utils import handle_error

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

    def _get_raw_klines(self, pair, limit="200", interval="1h"):
        params = {"symbol": pair, "interval": interval, "limit": limit}
        res = get(url=self.CANDLESTICK, params=params)
        handle_error(res)
        return res.json()

    def _ticker_price(self):
        r = get(url=self.TICKER_PRICE)
        return r.json()
