import os
from requests import request
from tools.handle_error import handle_binance_errors
from exchange_apis.binance import BinanceApi


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
