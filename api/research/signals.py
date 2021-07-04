import math

from api.tools.enum_definitions import EnumDefinitions


class Signals:
    def __init__(self):
        pass

    def _weak_signals(self, close_price, open_price, ma_7, ma_25, ma_100):
        """
        Weak bullying
        - This detects prices that go up and go down (both bullying and bearing)
        - Weak signals, as they happen more frequently and do not entail a lot of profit
        """
        signal_strength = None
        signal_side = None

        # MA-25 line crossed MA-7
        # Using isclose relative tolerance, as values don't usually match
        ma_25_crossed_7 = (
            True
            if math.isclose(ma_25[len(ma_25) - 1], ma_7[len(ma_7) - 1], rel_tol=1e-3)
            else False
        )
        # Bottom of candlestick crossed MA-100
        top_green_candle = True if close_price > ma_25[len(ma_25) - 1] else False
        # Tip of candlestick crossed MA-100
        bottom_green_candle = True if open_price < ma_25[len(ma_25) - 1] else False

        # Downward/Bearing conditions
        top_red_candle = True if open_price > ma_25[len(ma_25) - 1] else False
        bottom_red_candle = True if close_price < ma_25[len(ma_25) - 1] else False

        if ma_25_crossed_7:
            if top_green_candle and bottom_green_candle:
                signal_strength = "WEAK"
                signal_side = EnumDefinitions.order_side[0]

            if top_red_candle and bottom_red_candle:
                signal_strength = "WEAK"
                signal_side = EnumDefinitions.order_side[1]

        return signal_strength, signal_side

    def _strong_signals(self, close_price, open_price, ma_7, ma_25, ma_100):
        """
        Strong signals use the MA_100
        Happen less frequently, but there is a higher profit margin
        Higher volatility
        """

        signal_strength = None
        signal_side = None

        # MA-25 line crossed MA-100
        ma_25_crossed = (
            True
            if math.isclose(
                ma_25[len(ma_25) - 1], ma_100[len(ma_100) - 1], rel_tol=1e-3
            )
            else False
        )
        # MA-7 line crossed MA-100
        ma_7_crossed = (
            True
            if math.isclose(ma_7[len(ma_7) - 1], ma_100[len(ma_100) - 1], rel_tol=1e-3)
            else False
        )

        # Upward/Bullying conditions
        # Bottom of candlestick crossed MA-100
        top_green_candle = True if close_price > ma_100[len(ma_100) - 1] else False
        # Tip of candlestick crossed MA-100
        bottom_green_candle = True if open_price > ma_100[len(ma_100) - 1] else False
        # Second to last Tip of candlestick crossed MA-100
        previous_top_green_candle = (
            True if open_price > ma_100[len(ma_100) - 2] else False
        )

        # Downward/Bearing conditions‰
        # Bottom of red candlestick crossed MA-100
        top_red_candle = True if open_price < ma_100[len(ma_100) - 1] else False
        # Tip of red candlestick crossed MA-100
        bottom_red_candle = True if close_price < ma_100[len(ma_100) - 1] else False
        # Second to last Tip of candlestick crossed MA-100
        previous_bottom_red_candle = (
            True if close_price < ma_100[len(ma_100) - 2] else False
        )

        # Strong signals
        if ma_25_crossed and ma_7_crossed:
            if top_green_candle and bottom_green_candle and previous_top_green_candle:
                signal_strength = "STRONG"
                signal_side = EnumDefinitions.order_side[0]

            if top_red_candle and bottom_red_candle and previous_bottom_red_candle:
                signal_strength = "STRONG"
                signal_side = EnumDefinitions.order_side[1]

        return signal_strength, signal_side

    def get_signals(self, close_price, open_price, ma_7, ma_25, ma_100):
        signal_strength, signal_side = self._strong_signals(
            close_price, open_price, ma_7, ma_25, ma_100
        )

        if not signal_strength:
            signal_strength, signal_side = self._weak_signals(
                close_price, open_price, ma_7, ma_25, ma_100
            )

        return signal_strength, signal_side
