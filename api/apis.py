import hashlib
import hmac
import os
from urllib.parse import urlencode
from time import time
from requests import get, request
from tools.handle_error import handle_binance_errors, json_response, json_response_error
from py3cw.request import Py3CW

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
    ticker_price_url = f"{BASE}/api/v3/ticker/price"
    ticker24_url = f"{BASE}/api/v3/ticker/24hr"
    candlestick_url = f"{BASE}/api/v3/klines"
    order_url = f"{BASE}/api/v3/order"
    order_book_url = f"{BASE}/api/v3/depth"
    avg_price = f"{BASE}/api/v3/avgPrice"
    open_orders = f"{BASE}/api/v3/openOrders"
    all_orders_url = f"{BASE}/api/v3/allOrders"
    user_data_stream = f"{BASE}/api/v3/userDataStream"
    trade_fee = f"{BASE}/sapi/v1/asset/tradeFee"

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

    def signed_request(self, url, method="GET", payload={}, params={}):
        """
        USER_DATA, TRADE signed requests
        """
        query_string = urlencode(payload, True)
        timestamp = round(time() * 1000)
        headers = {"Content-Type": "application/json", "X-MBX-APIKEY": self.key}

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
        data = self.request(method, url=url, headers=headers, params=params)
        return data

    def request(self, method="GET", **args):
        """
        Standard request
        - No signed
        - No authorization
        """
        res = request(method, **args)
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
    bb_symbols_raw = f"{bb_base_url}/account/symbols"
    bb_bot_url = f"{bb_base_url}/bot"
    bb_activate_bot_url = f"{bb_base_url}/bot/activate"

    # paper-trading
    bb_paper_trading_url = f"{bb_base_url}/paper-trading"
    bb_paper_trading_activate_url = f"{bb_base_url}/paper-trading/activate"
    bb_paper_trading_deactivate_url = f"{bb_base_url}/paper-trading/deactivate"


    # Trade operations
    bb_buy_order_url = f"{bb_base_url}/order/buy"
    bb_buy_market_order_url = f"{bb_base_url}/order/buy/market"
    bb_sell_order_url = f"{bb_base_url}/order/sell"
    bb_opened_orders_url = f"{bb_base_url}/order/open"
    bb_close_order_url = f"{bb_base_url}/order/close"

    # balances
    bb_balance_url = f"{bb_base_url}/account/balance/raw"
    bb_balance_estimate_url = f"{bb_base_url}/account/balance/estimate"

    # research
    bb_autotrade_settings_url = f"{bb_base_url}/autotrade-settings/bots"
    bb_blacklist_url = f"{bb_base_url}/research/blacklist"

    def bb_request(self, url, method="GET", params=None, payload=None):
        """
        Standard request for binbot API endpoints
        Authentication required in the future
        """
        res = request(method, url=url, params=params, json=payload)
        data = handle_binance_errors(res)
        return data

class ThreeCommasApiError:
    """3commas.io API error"""

    def __init__(self, status):
        self.status = status

    def __str__(self):
        return "3commas API error: status={}".format(self.status)

class ThreeCommasApi:

    def get_marketplace_presets(self):
        p3cw = Py3CW(
            key=os.environ["3C_API_KEY"],
            secret=os.environ["3C_SECRET"]
        )
        error, data = p3cw.request(
            entity='marketplace',
            action="presets",
            payload={
                "sort_direction": "asc",
                "bot_strategy": "long",
                "profit_per_day_from": 1,
            }
        )
        if error:
            error = ThreeCommasApiError(error)
            return json_response_error(error)
        else:
            return json_response({"message": "Sucessfully retrieved preset bots!", "data": data["bots"]})

    def get_all_marketplace_item(self):
        p3cw = Py3CW(
            key=os.environ["3C_API_KEY"],
            secret=os.environ["3C_SECRET"]
        )
        error, data = p3cw.request(
            entity='marketplace',
            action="items",
            payload={
                "scope": "all",
                "limit": 1000,
                "offset": 0,
                "order": "newest",
                "locale": "en"
            }
        )

        if error:
            error = ThreeCommasApiError(error["msg"])
            return error
        else:
            return data

    def get_marketplace_item_signals(self, id):
        p3cw = Py3CW(
            key=os.environ["3C_API_KEY"],
            secret=os.environ["3C_SECRET"]
        )
        error, data = p3cw.request(
            entity='marketplace',
            action="signals",
            action_id=str(id),
        )

        if error:
            error = ThreeCommasApiError(error["msg"])
            return error
        else:
            return data
