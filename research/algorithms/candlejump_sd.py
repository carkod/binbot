import os

def candlejump_sd(close_price, open_price, ma_7, ma_100, ma_25, symbol, sd, value, chaikin_diff, regression, _send_msg, run_autotrade, ws, intercept):
    """
    Copy of ma_candlestick_jump but adjusted with standard deviation to avoid early close position
    """
    if (
        # float(close_price) > float(open_price)
        chaikin_diff < -3
        and sd > 0.8
        and float(intercept) > 10
        and close_price > ma_7[len(ma_7) - 1]
        and open_price > ma_7[len(ma_7) - 1]
        and close_price > ma_25[len(ma_25) - 1]
        and open_price > ma_25[len(ma_25) - 1]
        and ma_7[len(ma_7) - 1] > ma_7[len(ma_7) - 2]
        and close_price > ma_7[len(ma_7) - 2]
        and open_price > ma_7[len(ma_7) - 2]
        and close_price > ma_100[len(ma_100) - 1]
        and open_price > ma_100[len(ma_100) - 1]
        and close_price > ma_25[len(ma_25) - 1]
        and open_price > ma_25[len(ma_25) - 1]
    ):

        msg = f"- [{os.getenv('ENV')}] Candlesick <strong>jump SD-based algorithm</strong> #{symbol} \n - SD {sd} \n - Chaikin oscillator {value}, diff {'positive' if chaikin_diff >= 0 else 'negative'} \n - Regression line {regression} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots/new/{symbol}"
        _send_msg(msg)
        print(msg)

        run_autotrade(symbol, ws, "candlejump_sd", True, sd)
    
    return
