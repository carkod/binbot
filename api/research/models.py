class RCorrelationModel(dict):

    def __init__(self, r_market=None, r=0, p_value=0):
        self.r_market = r_market
        self.r = r
        self.p_value = p_value

    @property
    def get(self):
        return self.__dict__

class ResearchDataModel(dict):

    def __init__(self, market, current_price, volatility, last_volume, spread, price_change_24, candlestick_signal, signal_strength, signal_side, signal_timestamp):
        self.market = market
        self.r_correlation = RCorrelationModel(dict.r_correlation)
        # From market_data
        self.current_price = current_price,
        self.volatility = volatility,
        self.last_volume = last_volume,
        self.spread = spread,
        self.price_change_24 = price_change_24,  # MongoDB can't sort string decimals
        self.candlestick_signal = candlestick_signal,
        self.signal_strength = signal_strength
        self.signal_side = signal_side
        self.signal_timestamp = signal_timestamp


class BlackListedModel(dict):
    symbol = ""
    reason = ""
