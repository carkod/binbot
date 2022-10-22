import time

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
        updated_at: int = (time() * 1000),
        autotrade = 0,
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
        base_order_size = "15", # Assuming 10 USDT is the minimum, adding a bit more to avoid MIN_NOTIONAL fail
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
        self.base_order_size = base_order_size


class PaperAutotradeSettings(AutotradeSettingsModel):
    """
    Same as AutotradeSettingsModel but with different defaults
    """
    def __init__(
        self,
        base_order_size,
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
    ):
        super(PaperAutotradeSettings).__init__(
            PaperAutotradeSettings,
            base_order_size, # inherted from parent class
            _id,
            candlestick_interval,
            updated_at,
            autotrade,
            trailling,
            trailling_deviation,
            trailling_profit,
            stop_loss,
            take_profit,
            balance_to_use,
            balance_size_to_use,
            max_request,
            system_logs,
            update_required,
            telegram_signals,
            max_active_autotrade_bots
        )
