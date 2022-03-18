import os

def ma_candlestick_jump(close_price, open_price, ma_7, ma_100, ma_25, symbol, sd, value, chaikin_diff, regression, _send_msg, run_autotrade, ws):
    """
    Candlesticks are in an upward trending motion for several periods
    This algorithm checks last MAs to decide whether to trade
    """

    if (
        # It doesn't have to be a red candle for upward trending
        float(close_price) > float(open_price)
        and sd > 0.006
        and close_price > ma_7[len(ma_7) - 1]
        and open_price > ma_7[len(ma_7) - 1]
        and ma_7[len(ma_7) - 1] > ma_7[len(ma_7) - 2]
        and close_price > ma_7[len(ma_7) - 2]
        and open_price > ma_7[len(ma_7) - 2]
        and ma_7[len(ma_7) - 2] > ma_7[len(ma_7) - 3]
        and close_price > ma_7[len(ma_7) - 3]
        and open_price > ma_7[len(ma_7) - 3]
        and close_price > ma_100[len(ma_100) - 1]
        and open_price > ma_100[len(ma_100) - 1]
        and close_price > ma_25[len(ma_25) - 1]
        and open_price > ma_25[len(ma_25) - 1]
        and close_price > ma_25[len(ma_25) - 2]
        and open_price > ma_25[len(ma_25) - 2]
    ):

        # status = "strong upward trend"
        msg = f"- [{os.getenv('ENV')}] Candlesick <strong>jump algorithm</strong> {symbol} \n - SD {sd} \n - Chaikin oscillator {value}, diff {'positive' if chaikin_diff >= 0 else 'negative'} \n - Regression line {regression} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"
        _send_msg(msg)
        print(msg)

        run_autotrade(symbol, ws)
    
    return
