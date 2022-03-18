import math
import os

def candlestick_patterns(reversal, sd, close_price, open_price, value, chaikin_diff, regression, downtrend, all_patterns, _send_msg, run_autotrade, symbol, ws):
    """
    Uses candlestick pattern dection by TA-lib
    """

    # Looking at graphs, sd > 0.006 tend to give at least 3% up and down movement
    if reversal and math.ceil(sd) > 0.006 and len(downtrend) == 0 and float(close_price) > float(open_price):
        status = f"reversal confirmation "
        if len(all_patterns) > 0:
            for p in all_patterns:
                status += f"\n- {p} pattern"
                msg = f"- [{os.getenv('ENV')}] Candlestick pattern <strong>{status}</strong> {symbol} \n - SD {sd} \n - Chaikin oscillator {value}, diff {'positive' if chaikin_diff >= 0 else 'negative'} \n - Regression line {regression} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"
                _send_msg(msg)
                print(msg)

                run_autotrade(symbol, ws)
    return