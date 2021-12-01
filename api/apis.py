import hashlib
import hmac
import os
from urllib.parse import urlencode
from time import time
from requests import Session, get, request
from api.tools.handle_error import handle_binance_errors


class BinanceApi:
    """
    Binance API URLs

    To test:
    https://binance.github.io/binance-api-swagger/
    """

    BASE = "https://api.binance.com"
    WAPI = f"{BASE}/api/v3/depth"
    WS_BASE = "wss://stream.binance.com:9443/stream?streams="

    recvWindow = 9000
    secret = os.getenv("BINANCE_SECRET")
    key = os.getenv("BINANCE_KEY")
    server_time_url = f"{BASE}/api/v3/time"
    account_url = f"{BASE}/api/v3/account"
    exchangeinfo_url = f"{BASE}/api/v3/exchangeInfo"
    ticker_price = f"{BASE}/api/v3/ticker/price"
    ticker24_url = f"{BASE}/api/v3/ticker/24hr"
    candlestick_url = f"{BASE}/api/v3/klines"
    order_url = f"{BASE}/api/v3/order"
    order_book_url = f"{BASE}/api/v3/depth"
    avg_price = f"{BASE}/api/v3/avgPrice"
    open_orders = f"{BASE}/api/v3/openOrders"
    all_orders_url = f"{BASE}/api/v3/allOrders"
    user_data_stream = f"{BASE}/api/v3/userDataStream"
    trade_fee = f"{BASE}/sapi/v1/asset/tradeFee"

    user_data_stream = f"{BASE}/api/v3/userDataStream"
    streams_url = f"{WS_BASE}"

    withdraw_url = f"{BASE}/wapi/v3/withdraw.html"
    withdraw_history_url = f"{BASE}/wapi/v3/withdrawHistory.html"
    deposit_history_url = f"{BASE}/wapi/v3/depositHistory.html"
    deposit_address_url = f"{BASE}/wapi/v3/depositAddress.html"

    dust_transfer_url = f"{BASE}/sapi/v1/asset/dust"
    account_snapshot_url = f"{BASE}/sapi/v1/accountSnapshot"

    def get_server_time(self):
        data = self.request(url=self.server_time_url)
        return data["serverTime"]

    def signed_request(self, url, method="GET", payload={}):
        """
        USER_DATA, TRADE signed requests
        """
        session = Session()
        query_string = urlencode(payload, True)
        timestamp = round(time() * 1000)
        session.headers.update(
            {"Content-Type": "application/json", "X-MBX-APIKEY": self.key}
        )

        if query_string:
            query_string = (
                f"{query_string}&recvWindow={self.recvWindow}&timestamp={timestamp}"
            )
        else:
            query_string = f"recvWindow={self.recvWindow}&timestamp={timestamp}"

        signature = hmac.new(
            self.secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        url = f"{url}?{query_string}&signature={signature}"
        res = session.request(method, url=url)
        data = handle_binance_errors(res)
        return data

    def request(self, url, method="GET", params=None, json=None):
        """
        Standard request
        - No signed
        - No authorization
        """
        res = request(method, url=url, params=params, json=json)
        data = handle_binance_errors(res)
        return data


class BinbotApi(BinanceApi):
    """
    API endpoints on this project itself
    includes Binance Api
    """

    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
    bb_candlestick_url = f"{bb_base_url}/charts/candlestick"
    bb_24_ticker_url = f"{bb_base_url}/account/ticker24"
    bb_symbols_raw = f"{bb_base_url}/account/symbols/raw"
    bb_bot_url = f"{bb_base_url}/bot"
    bb_activate_bot_url = f"{bb_base_url}/bot/activate"

    # Trade operations
    bb_buy_order_url = f"{bb_base_url}/order/buy"
    bb_tp_buy_order_url = f"{bb_base_url}/order/buy/take-profit"
    bb_buy_market_order_url = f"{bb_base_url}/order/buy/market"
    bb_sell_order_url = f"{bb_base_url}/order/sell"
    bb_tp_sell_order_url = f"{bb_base_url}/order/sell/take-profit"
    bb_sell_market_order_url = f"{bb_base_url}/order/sell/market"
    bb_opened_orders_url = f"{bb_base_url}/order/open"
    bb_close_order_url = f"{bb_base_url}/order/close"
    bb_stop_buy_order_url = f"{bb_base_url}/order/buy/stop-limit"
    bb_stop_sell_order_url = f"{bb_base_url}/order/sell/stop-limit"

    # balances
    bb_balance_url = f"{bb_base_url}/account/balance/raw"
    bb_balance_estimate_url = f"{bb_base_url}/account/balance/estimate"

    # research
    bb_controller_url = f"{bb_base_url}/research/controller"
    bb_blacklist_url = f"{bb_base_url}/research/blacklist"

    def bb_request(self, url, method="GET", params=None, payload=None):
        """
        Standard request for binbot API endpoints
        Authentication required in the future
        """
        res = request(method, url=url, params=params, json=payload)
        data = handle_binance_errors(res)
        return data


class CoinBaseApi:
    """
    Currency and Cryptocurrency conversion service
    """

    BASE = "https://api.coinbase.com/v2"
    EXG_URL = f"{BASE}/prices"

    def get_conversion(self, time, base="BTC", quote="GBP"):

        params = {
            "apikey": os.environ["COINAPI_KEY"],
            "date": time.strftime("%Y-%m-%d"),
        }
        url = f"{self.EXG_URL}/{base}-{quote}/spot"
        data = get(url, params).json()
        try:
            data["data"]["amount"]
        except KeyError as e:
            print(e)
        rate = float(data["data"]["amount"])
        return rate
