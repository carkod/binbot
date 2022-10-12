class AutotradeSettingsModel:
    """
    Blueprint autotrade settings (research_controller) collection on MongoDB
    All validation and database fields new or old handled here
    """
    def __init__(
        self,
        trailling: str = "true",
        _id = "settings",
        candlestick_interval: str = "15m",
        updated_at: int = time() * 1000,
        autotrade = 0,
        trailling = 'false',
        trailling_deviation = 3,
        trailling_profit = 2.4,
        stop_loss = 0,
        take_profit = 2.4,
        balance_to_use = 'USDT',
        balance_size_to_use = '100',
        max_request = 950,
        system_logs = [],
        update_required = False,
        telegram_signals = 1,
        max_active_autotrade_bots = 15,
        base_order_size = "15" # Assuming 10 USDT is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
        *args,
        **kwargs
    ) -> None:
        self._id = _id,
        self.candlestick_interval = candlestick_interval,
        self.updated_at = updated_at,
        self.autotrade = autotrade,
        self.trailling = trailling,
        self.trailling_deviation = trailling_deviation,
        self.trailling_profit = trailling_profit,
        self.stop_loss = stop_loss,
        self.take_profit = take_profit,
        self.balance_to_use = balance_to_use,
        self.balance_size_to_use = balance_size_to_use,
        self.max_request = max_request,
        self.system_logs = system_logs,
        self.update_required = update_required,
        self.telegram_signals = telegram_signals,
        self.max_active_autotrade_bots = max_active_autotrade_bots,


class PaperAutotradeSettings(AutotradeSettingsModel):
    """
    Same as AutotradeSettingsModel but with different defaults
    """
    def __init__(
        self,
        _id = "test_autotrade_settings", # always the same
        candlestick_interval: str = "15m",
        updated_at: int = time() * 1000,
        autotrade = 1, # Since this is not using real money, it can always be active
        trailling = 'true', # true or false string, always activate to test bots
        trailling_deviation = 3,
        trailling_profit = 2.4,
        stop_loss = 0,
        take_profit = 2.4,
        balance_to_use = 'USDT',
        balance_size_to_use = '100',
        max_request = 950,
        system_logs = [],
        update_required = False,
        telegram_signals = 1,
        max_active_autotrade_bots = 15,
        base_order_size,
    ):
        super(
            PaperAutotradeSettings,
            self._id = _id,
            self.candlestick_interval = candlestick_interval,
            self.updated_at = updated_at,
            self.autotrade = autotrade,
            self.trailling = trailling,
            self.trailling_deviation = trailling_deviation,
            self.trailling_profit = trailling_profit,
            self.stop_loss = stop_loss,
            self.take_profit = take_profit,
            self.balance_to_use = balance_to_use,
            self.balance_size_to_use = balance_size_to_use,
            self.max_request = max_request,
            self.system_logs = system_logs,
            self.update_required = update_required,
            self.telegram_signals = telegram_signals,
            self.max_active_autotrade_bots = max_active_autotrade_bots,
            self.base_order_size = base_order_size, # Inherit from parent class
        ).__init__()


class RCorrelationModel(dict):
    def __init__(self, r_market=None, r=0, p_value=0):
        self.r_market = r_market
        self.r = r
        self.p_value = p_value

    @property
    def get(self):
        return self.__dict__


class ResearchDataModel(dict):
    def __init__(
        self,
        market,
        current_price,
        volatility,
        last_volume,
        spread,
        price_change_24,
        candlestick_signal,
        signal_strength,
        signal_side,
        signal_timestamp,
    ):
        self.market = market
        self.r_correlation = RCorrelationModel(dict.r_correlation)
        # From market_data
        self.current_price = current_price
        self.volatility = volatility
        self.last_volume = last_volume
        self.spread = spread
        self.price_change_24 = price_change_24  # MongoDB can't sort string decimals
        self.candlestick_signal = candlestick_signal
        self.signal_strength = signal_strength
        self.signal_side = signal_side
        self.signal_timestamp = signal_timestamp


class BlackListedModel(dict):
    symbol = ""
    reason = ""
