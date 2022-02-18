import hashlib
import hmac
import os
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from requests import Session, get

from utils import handle_binance_errors
from dotenv import load_dotenv

load_dotenv()


class BinanceApi:
    """
    Binance Api URLs
    """

    BASE = "https://api3.binance.com"
    WAPI = f"{BASE}/api/v3/depth"
    WS_BASE = "wss://stream.binance.com:9443/stream?streams="

    recvWindow = 5000
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

    user_data_stream = f"{BASE}/api/v3/userDataStream"
    streams_url = f"{WS_BASE}"

    withdraw_url = f"{BASE}/wapi/v3/withdraw.html"
    withdraw_history_url = f"{BASE}/wapi/v3/withdrawHistory.html"
    deposit_history_url = f"{BASE}/wapi/v3/depositHistory.html"
    deposit_address_url = f"{BASE}/wapi/v3/depositAddress.html"

    dust_transfer_url = f"{BASE}/sapi/v1/asset/dust"
    account_snapshot_url = f"{BASE}/sapi/v1/accountSnapshot"
    launchpool_url = (
        "https://launchpad.binance.com/gateway-api/v1/public/launchpool/project/list"
    )

    def get_server_time(self):
        response = get(url=self.server_time_url)
        data = handle_binance_errors(response)
        return data["serverTime"]

    def signed_request(self, url, method="GET", payload={}):
        """
        USER_DATA, TRADE signed requests
        """
        session = Session()
        query_string = urlencode(payload, True)
        timestamp = self.get_server_time()
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

    def _exchange_info(self, symbol=None):
        """
        Copied from /api/account/account.py
        To be refactored in the future
        """
        params = None
        if symbol:
            params = {"symbol": symbol}

        exchange_info = get(url=self.exchangeinfo_url, params=params).json()
        return exchange_info

    def _get_raw_klines(self, pair, limit="200", interval="1h"):
        params = {"symbol": pair, "interval": interval, "limit": limit}
        res = get(url=self.candlestick_url, params=params)
        handle_binance_errors(res)
        return res.json()

    def ticker_price(self, symbol=None):
        """
        Weight 2 (v3). Ideal for list of symbols
        """
        params = None
        if symbol:
            params = {"symbol": symbol}
        r = get(url=self.ticker_price_url, params=params)
        response = handle_binance_errors(r)
        return response

    def launchpool_projects(self):
        res = get(url=self.launchpool_url, headers={"User-Agent": "Mozilla"})
        data = handle_binance_errors(res)
        return data

    def price_precision(self, symbol):
        """
        Modified from price_filter_by_symbol
        from /api/account/account.py

        This function always will use the tickSize decimals
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        price_filter = next(
            (m for m in market["filters"] if m["filterType"] == "PRICE_FILTER"), None
        )

        # Once got the filter data of Binance
        # Transform into string and remove leading zeros
        # This is how the exchange accepts the prices, it will not work with scientific exponential notation e.g. 2.1-10
        price_precision = Decimal(str(price_filter["tickSize"].rstrip(".0")))

        # Finally return the correct number of decimals required
        return -(price_precision).as_tuple().exponent

    def min_amount_check(self, symbol, qty):
        """
        Min amout check
        Uses MIN notional restriction (price x quantity) from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - Use current ticker price for price
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        min_notional_filter = next(
            (m for m in market["filters"] if m["filterType"] == "MIN_NOTIONAL"), None
        )
        min_qty = float(qty) > float(min_notional_filter["minNotional"])
        return min_qty

    def find_baseAsset(self, symbol):
        symbols = self._exchange_info(symbol)
        base_asset = symbols["symbols"][0]["baseAsset"]
        return base_asset

    def find_quoteAsset(self, symbol):
        symbols = self._exchange_info(symbol)
        quote_asset = symbols["symbols"][0]
        if quote_asset:
            quote_asset = quote_asset["quoteAsset"]
        return quote_asset


class BinbotApi(BinanceApi):
    """
    API endpoints on this project itself
    includes Binance Api
    """

    bb_base_url = os.getenv("FLASK_DOMAIN")
    bb_candlestick_url = f"{bb_base_url}/charts/candlestick"
    bb_klines = f"{bb_base_url}/charts/klines"
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
    bb_balance_series_url = f"{bb_base_url}/account/balance/series"

    # research
    bb_controller_url = f"{bb_base_url}/research/controller"
    bb_blacklist_url = f"{bb_base_url}/research/blacklist"

    def _get_24_ticker(self, market):
        url = f"{self.bb_24_ticker_url}/{market}"
        res = get(url=url)
        data = handle_binance_errors(res)
        return data

    def _get_candlestick(self, market, interval, stats=None):
        url = f"{self.bb_candlestick_url}/{market}/{interval}"
        if stats:
            url = f"{self.bb_candlestick_url}/{market}/{interval}/{stats}"
        res = get(url=url)
        data = handle_binance_errors(res)
        return data


class CoinBaseApi:
    """
    Currency and Cryptocurrency conversion service
    """

    BASE = "https://api.coinbase.com/v2"
    EXG_URL = f"{BASE}/prices"

    def get_conversion(self, base="BTC", quote="GBP", time=datetime.now()):

        params = {
            "apikey": os.environ["COINAPI_KEY"],
            "date": time.strftime("%Y-%m-%d"),
        }
        url = f"{self.EXG_URL}/{base}-{quote}/spot"
        data = get(url, params).json()
        try:
            data["data"]["amount"]
        except KeyError:
            print(data)

        rate = float(data["data"]["amount"])
        return rate
