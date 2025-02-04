import hashlib
import hmac
import os
from random import randrange
from urllib.parse import urlencode
from requests import Session, request
from tools.handle_error import handle_binance_errors, json_response, json_response_error
from tools.exceptions import IsolateBalanceError
from py3cw.request import Py3CW
from requests_cache import MongoCache
from pymongo import MongoClient
from decimal import Decimal


class BinanceApi:
    """
    Binance API URLs
    https://binance.github.io/binance-api-swagger/
    """

    api_servers = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api3.binance.com",
        "https://api-gcp.binance.com",
    ]
    market_api_servers = ["https://data-api.binance.vision", "https://api3.binance.com"]
    BASE = api_servers[randrange(2) - 1]
    MARKET_DATA_BASE = market_api_servers[randrange(3) - 1]
    WAPI = f"{BASE}/api/v3/depth"
    WS_BASE = "wss://stream.binance.com:9443/stream?streams="

    recvWindow = 9000
    secret: str = os.getenv("BINANCE_SECRET", "abc")
    key: str = os.getenv("BINANCE_KEY", "abc")
    server_time_url = f"{MARKET_DATA_BASE}/api/v3/time"
    # Binance always returning forbidden for other APIs
    account_url = f"{api_servers[1]}/api/v3/account"
    exchangeinfo_url = f"{MARKET_DATA_BASE}/api/v3/exchangeInfo"
    ticker_price_url = f"{MARKET_DATA_BASE}/api/v3/ticker/price"
    ticker24_url = f"{MARKET_DATA_BASE}/api/v3/ticker/24hr"
    candlestick_url = f"{MARKET_DATA_BASE}/api/v3/uiKlines"
    order_url = f"{BASE}/api/v3/order"
    order_book_url = f"{BASE}/api/v3/depth"
    avg_price = f"{BASE}/api/v3/avgPrice"
    open_orders = f"{BASE}/api/v3/openOrders"
    all_orders_url = f"{BASE}/api/v3/allOrders"
    cancel_replace_url = f"{BASE}/api/v3/order/cancelReplace"
    trade_fee = f"{BASE}/sapi/v1/asset/tradeFee"
    wallet_balance_url = f"{BASE}/sapi/v1/asset/wallet/balance"
    user_asset_url = f"{BASE}/sapi/v3/asset/getUserAsset"

    # order, user data, only works with api.binance host
    user_data_stream = "https://api.binance.com/api/v3/userDataStream"

    withdraw_url = f"{BASE}/wapi/v3/withdraw.html"
    withdraw_history_url = f"{BASE}/wapi/v3/withdrawHistory.html"
    deposit_history_url = f"{BASE}/wapi/v3/depositHistory.html"
    deposit_address_url = f"{BASE}/wapi/v3/depositAddress.html"

    dust_transfer_url = f"{BASE}/sapi/v1/asset/dust"
    account_snapshot_url = f"{BASE}/sapi/v1/accountSnapshot"

    # Margin
    isolated_fee_url = f"{BASE}/sapi/v1/margin/isolatedMarginData"
    isolated_account_url = f"{BASE}/sapi/v1/margin/isolated/account"
    margin_isolated_transfer_url = f"{BASE}/sapi/v1/margin/isolated/transfer"
    loan_record_url = f"{BASE}/sapi/v1/margin/borrow-repay"
    isolated_hourly_interest = f"{BASE}/sapi/v1/margin/next-hourly-interest-rate"
    margin_order = f"{BASE}/sapi/v1/margin/order"
    max_borrow_url = f"{BASE}/sapi/v1/margin/maxBorrowable"
    interest_history_url = f"{BASE}/sapi/v1/margin/interestHistory"

    def setup_mongocache(self):
        mongo: MongoClient = MongoClient(
            host=os.getenv("MONGO_HOSTNAME"),
            port=int(os.getenv("MONGO_PORT", 2017)),
            authSource="admin",
            username=os.getenv("MONGO_AUTH_USERNAME"),
            password=os.getenv("MONGO_AUTH_PASSWORD"),
        )
        mongo_cache = MongoCache(connection=mongo)
        return mongo_cache

    def request(
        self,
        url,
        method="GET",
        session: Session | None = None,
        payload: dict | None = None,
        **kwargs,
    ):
        """
        Standard request
        - No signed
        - No authorization
        """
        if session:
            res = session.request(method=method, url=url, **kwargs)
        else:
            res = request(method=method, url=url, json=payload, **kwargs)
        data = handle_binance_errors(res)
        return data

    def get_server_time(self):
        data = self.request(url=self.server_time_url)
        return data["serverTime"]

    def signed_request(self, url, method="GET", payload: dict = {}) -> dict:
        """
        USER_DATA, TRADE signed requests

        Arguments are all the same as requests
        except payload, which is centrally formatted
        here to become a JSON
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
        data = self.request(url, method, session)
        return data

    def get_listen_key(self):
        """
        Get user data websocket stream
        """
        headers = {"Content-Type": "application/json", "X-MBX-APIKEY": self.key}
        res = request(method="POST", url=self.user_data_stream, headers=headers)
        response = handle_binance_errors(res)
        listen_key = response["listenKey"]
        return listen_key

    """
    No security endpoints
    """

    def _exchange_info(self, symbol=None):
        """
        This must be a separate method because classes use it with inheritance

        This request is used in many places to retrieve data about symbols, precisions etc.
        It is a high weight endpoint, thus Binance could ban our IP
        However it is not real-time updated data, so cache is used to avoid hitting endpoint
        too many times and still be able to re-request data everywhere.

        In addition, it uses MongoDB, with a separate database called "mongo_cache"
        """
        params = {}
        if symbol:
            params["symbol"] = symbol

        # mongo_cache = self.setup_mongocache()
        # set up a cache that expires in 1440'' (24hrs)
        # session = CachedSession("http_cache", backend=mongo_cache, expire_after=1440)
        exchange_info_res = self.request(url=f"{self.exchangeinfo_url}", params=params)
        # exchange_info = handle_binance_errors(exchange_info_res)
        return exchange_info_res

    def price_filter_by_symbol(self, symbol, filter_limit):
        """
        PRICE_FILTER restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - filter_limit: string - minPrice or maxPrice
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        price_filter = next(
            (m for m in market["filters"] if m["filterType"] == "PRICE_FILTER")
        )
        return price_filter[filter_limit].rstrip(".0")

    def lot_size_by_symbol(self, symbol, lot_size_limit):
        """
        LOT_SIZE (quantity) restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - lot_size_limit: string - minQty, maxQty, stepSize
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        quantity_filter: list = next(
            (m for m in market["filters"] if m["filterType"] == "LOT_SIZE")
        )
        return quantity_filter[lot_size_limit].rstrip(".0")

    def min_notional_by_symbol(self, symbol, min_notional_limit="minNotional"):
        """
        MIN_NOTIONAL (price x quantity) restrictions from /exchangeinfo
        @params:
            - symbol: string - pair/market e.g. BNBBTC
            - min_notional_limit: string - minNotional
        """
        symbols = self._exchange_info(symbol)
        market = symbols["symbols"][0]
        min_notional_filter = next(
            m for m in market["filters"] if m["filterType"] == "NOTIONAL"
        )
        return min_notional_filter[min_notional_limit]

    def calculate_price_precision(self, symbol) -> int:
        precision = -1 * (
            Decimal(str(self.price_filter_by_symbol(symbol, "tickSize")))
            .as_tuple()
            .exponent
        )
        price_precision = int(precision)
        return price_precision

    def calculate_qty_precision(self, symbol) -> int:
        precision = -1 * (
            Decimal(str(self.lot_size_by_symbol(symbol, "stepSize")))
            .as_tuple()
            .exponent
        )
        qty_precision = int(precision)
        return qty_precision

    def find_quoteAsset(self, symbol):
        """
        e.g. BNBBTC: base asset = BTC
        """
        symbols = self._exchange_info(symbol)
        quote_asset = symbols["symbols"][0]
        if quote_asset:
            quote_asset = quote_asset["quoteAsset"]
        return quote_asset

    def find_baseAsset(self, symbol):
        """
        e.g. BNBBTC: base asset = BNB
        """
        symbols = self._exchange_info(symbol)
        base_asset = symbols["symbols"][0]["baseAsset"]
        return base_asset

    def ticker(self, symbol: str | None = None, json: bool = True):
        params = {}
        if symbol:
            params = {"symbol": symbol}
        data = self.request(url=self.ticker_price_url, params=params)
        if json:
            return json_response({"data": data})
        else:
            return data

    def ticker_24(self, type: str = "FULL", symbol: str | None = None):
        """
        Weight 40 without symbol
        https://github.com/carkod/binbot/issues/438

        Using cache
        """
        params = {"type": type}
        if symbol:
            params["symbol"] = symbol

        # mongo_cache = self.setup_mongocache()
        # # because candlesticks are 15m
        # session = CachedSession('ticker_24_cache', backend=mongo_cache, expire_after=15)
        data = self.request(url=self.ticker24_url, params=params)
        return data

    def get_raw_klines(
        self, symbol, interval, limit=500, start_time=None, end_time=None
    ):
        """
        Get raw klines
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = self.request(url=self.candlestick_url, params=params)
        return data

    """
    USER_DATA endpoints
    """

    def get_account_balance(self):
        """
        Get account balance
        """
        payload = {"omitZeroBalances": "true"}
        data = self.signed_request(self.account_url, payload=payload)
        return data

    def get_wallet_balance(self):
        """
        Balance by wallet (SPOT, FUNDING, CROSS MARGIN...)
        https://binance-docs.github.io/apidocs/spot/en/#query-user-wallet-balance-user_data

        This is a consolidated balance across all account
        so it doesn't require us to retrieve isolated margin, cross margin, etc, separately.
        """
        data = self.signed_request(self.wallet_balance_url)
        return data

    def cancel_margin_order(self, symbol: str, order_id: int):
        return self.signed_request(
            self.margin_order,
            method="DELETE",
            payload={"symbol": symbol, "orderId": str(order_id), "isIsolated": "TRUE"},
        )

    def enable_isolated_margin_account(self, symbol):
        return self.signed_request(
            self.isolated_account_url, method="POST", payload={"symbol": symbol}
        )

    def disable_isolated_margin_account(self, symbol):
        """
        Very high weight, use as little as possible

        There is a cronjob that disables all margin isolated accounts everyday
        check market_updates
        """
        return self.signed_request(
            self.isolated_account_url, method="DELETE", payload={"symbol": symbol}
        )

    def get_isolated_account(self, symbol):
        """
        https://developers.binance.com/docs/margin_trading/account/Query-Isolated-Margin-Account-Info
        Request weight: 10(IP)
        """
        return self.signed_request(
            self.isolated_account_url, payload={"symbol": symbol}
        )

    def transfer_isolated_margin_to_spot(self, asset, symbol, amount):
        return self.signed_request(
            self.margin_isolated_transfer_url,
            method="POST",
            payload={
                "transFrom": "ISOLATED_MARGIN",
                "transTo": "SPOT",
                "asset": asset,
                "symbol": symbol,
                "amount": amount,
            },
        )

    def transfer_spot_to_isolated_margin(self, asset: str, symbol: str, amount: float):
        return self.signed_request(
            self.margin_isolated_transfer_url,
            method="POST",
            payload={
                "transFrom": "SPOT",
                "transTo": "ISOLATED_MARGIN",
                "asset": asset,
                "symbol": symbol,
                "amount": str(amount),
            },
        )

    def create_margin_loan(self, asset, symbol, amount, isIsolated=True):
        if not isIsolated:
            isIsolated = "FALSE"
        else:
            isIsolated = "TRUE"

        return self.signed_request(
            self.loan_record_url,
            method="POST",
            payload={
                "asset": asset,
                "symbol": symbol,
                "amount": amount,
                "isIsolated": isIsolated,
                "type": "BORROW",
            },
        )

    def get_max_borrow(self, asset, isolated_symbol: str | None = None):
        return self.signed_request(
            self.max_borrow_url,
            payload={"asset": asset, "isolatedSymbol": isolated_symbol},
        )

    def get_margin_loan_details(self, loan_id: int, symbol: str):
        return self.signed_request(
            self.loan_record_url,
            payload={
                "txId": loan_id,
                "type": "BORROW",
                "isolatedSymbol": symbol,
            },
        )

    def get_repay_details(self, loan_id: int, symbol: str):
        return self.signed_request(
            self.loan_record_url,
            payload={
                "txId": loan_id,
                "type": "REPAY",
                "isolatedSymbol": symbol,
            },
        )

    def repay_margin_loan(
        self, asset: str, symbol: str, amount: float | int, isIsolated: str = "TRUE"
    ):
        return self.signed_request(
            self.loan_record_url,
            method="POST",
            payload={
                "asset": asset,
                "isIsolated": isIsolated,
                "symbol": symbol,
                "amount": amount,
                "type": "REPAY",
            },
        )

    def get_interest_history(self, asset: str, symbol: str):
        return self.signed_request(
            self.interest_history_url,
            payload={"asset": asset, "isolatedSymbol": symbol},
        )

    def get_isolated_balance(self, symbol=None) -> list:
        """
        Get balance of Isolated Margin account

        Use isolated margin account is preferrable,
        because this is the one that supports the most assets
        """
        payload = {}
        if symbol:
            payload["symbols"] = [symbol]
        info = self.signed_request(url=self.isolated_account_url, payload=payload)
        assets = info["assets"]
        if len(assets) == 0:
            raise IsolateBalanceError(
                "Hit symbol 24hr restriction or not available (requires transfer in)"
            )
        return assets

    def get_isolated_balance_total(self):
        """
        Get balance of Isolated Margin account

        Use isolated margin account is preferrable,
        because this is the one that supports the most assets
        """
        info = self.signed_request(url=self.isolated_account_url, payload={})
        assets = info["totalNetAssetOfBtc"]
        if len(assets) == 0:
            raise IsolateBalanceError(
                "Hit symbol 24hr restriction or not available (requires transfer in)"
            )
        return assets

    def transfer_dust(self, assets: list[str]):
        """
        Transform small balances to BNB
        """
        list_assets = ",".join(assets)
        response = self.signed_request(
            url=self.dust_transfer_url, method="POST", payload={"asset": list_assets}
        )
        return response

    def query_open_orders(self, symbol):
        """
        Get current open orders

        This is a high weight endpoint IP Weight: 20
        https://binance-docs.github.io/apidocs/spot/en/#current-open-orders-user_data
        """
        open_orders = self.signed_request(self.open_orders, payload={"symbol": symbol})
        return open_orders

    def get_all_orders(self, symbol, order_id: int = 0, start_time=None):
        """
        Get all orders given symbol and order_id

        This is a high weight endpoint IP Weight: 20
        https://binance-docs.github.io/apidocs/spot/en/#all-orders-user_data

        Args:
        - symbol: str
        - order_id: int
        - start_time
        - end_time

        At least one of order_id or (start_time and end_time) must be sent
        """
        if order_id > 0:
            return self.signed_request(
                self.all_orders_url, payload={"symbol": symbol, "orderId": order_id}
            )

        elif start_time:
            return self.signed_request(
                self.all_orders_url, payload={"symbol": symbol, "startTime": start_time}
            )

        else:
            raise ValueError(
                "At least one of order_id or (start_time and end_time) must be sent"
            )

    def delete_opened_order(self, symbol, order_id):
        """
        Cancel single order
        """
        return self.signed_request(
            self.order_url,
            method="DELETE",
            payload={"symbol": symbol, "orderId": order_id},
        )

    def get_book_depth(self, symbol: str):
        """
        Get order book for a given symbol
        """
        data = self.request(url=f"{self.order_book_url}?symbol={symbol}")
        return data

    def get_user_asset(self, asset: str, need_btc_valuation: bool = False):
        """
        Get user asset

        https://developers.binance.com/docs/wallet/asset/user-assets
        response:
        {
            "asset": "AVAX",
            "free": "1",
            "locked": "0",
            "freeze": "0",
            "withdrawing": "0",
            "ipoable": "0",
            "btcValuation": "0"
        },
        """
        data = self.signed_request(
            url=self.user_asset_url,
            method="POST",
            payload={"asset": asset, "needBtcValuation": need_btc_valuation},
        )
        return data


class BinbotApi(BinanceApi):
    """
    API endpoints on this project itself
    includes Binance Api
    """

    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
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
    bb_sell_market_order_url = f"{bb_base_url}/order/sell/market"
    bb_opened_orders_url = f"{bb_base_url}/order/open"
    bb_close_order_url = f"{bb_base_url}/order/close"

    # balances
    bb_balance_url = f"{bb_base_url}/account/balance/raw"
    bb_balance_estimate_url = f"{bb_base_url}/account/balance/estimate"
    bb_liquidation_url = f"{bb_base_url}/account/one-click-liquidation"

    # research
    bb_autotrade_settings_url = f"{bb_base_url}/autotrade-settings/bots"
    bb_blacklist_url = f"{bb_base_url}/research/blacklist"
    bb_market_domination = f"{bb_base_url}/charts/market-domination"

    def bb_request(self, url, method="GET", params=None, payload=None):
        """
        Standard request for binbot API endpoints
        Authentication required in the future
        """
        res = request(method, url=url, params=params, json=payload)
        data = handle_binance_errors(res)
        return data

    def get_market_domination_series(self):
        result = self.bb_request(url=self.bb_market_domination, params={"size": 7})
        return result


class ThreeCommasApiError:
    """3commas.io API error"""

    def __init__(self, status):
        self.status = status

    def __str__(self):
        return "3commas API error: status={}".format(self.status)


class ThreeCommasApi:
    def get_marketplace_presets(self):
        p3cw = Py3CW(key=os.environ["3C_API_KEY"], secret=os.environ["3C_SECRET"])
        error, data = p3cw.request(
            entity="marketplace",
            action="presets",
            payload={
                "sort_direction": "asc",
                "bot_strategy": "long",
                "profit_per_day_from": 1,
            },
        )
        if error:
            error = ThreeCommasApiError(error)
            return json_response_error(error)
        else:
            return json_response(
                {"message": "Sucessfully retrieved preset bots!", "data": data["bots"]}
            )

    def get_all_marketplace_item(self):
        p3cw = Py3CW(key=os.environ["3C_API_KEY"], secret=os.environ["3C_SECRET"])
        error, data = p3cw.request(
            entity="marketplace",
            action="items",
            payload={
                "scope": "all",
                "limit": 1000,
                "offset": 0,
                "order": "newest",
                "locale": "en",
            },
        )

        if error:
            error = ThreeCommasApiError(error["msg"])
            return error
        else:
            return data

    def get_marketplace_item_signals(self, id):
        p3cw = Py3CW(key=os.environ["3C_API_KEY"], secret=os.environ["3C_SECRET"])
        error, data = p3cw.request(
            entity="marketplace",
            action="signals",
            action_id=str(id),
        )

        if error:
            error = ThreeCommasApiError(error["msg"])
            return error
        else:
            return data
