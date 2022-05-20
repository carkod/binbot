import os

from pattern_detection import downtrend_patterns, reversal_confirmation

def candlestick_patterns(data, sd, close_price, open_price, value, chaikin_diff, regression, _send_msg, run_autotrade, symbol, ws, intercept, ma_25):
    """
    Uses candlestick pattern dection by TA-lib
    """

    reversal = reversal_confirmation(data)
    downtrend = downtrend_patterns(data)

    # Looking at graphs, sd > 0.006 tend to give at least 3% up and down movement
    # if reversal and (round(sd * 10000) / 10000) > 0.006 and len(downtrend) == 0 and chaikin_diff < 0 and len(all_patterns) > 0:
    if reversal and chaikin_diff < 0 and float(intercept) > 5 and len(downtrend) == 0 and close_price > ma_25[len(ma_25) - 1]:
        status = f"reversal confirmation "
        # for p in all_patterns:
        # status += f"\n- {p} pattern"
        msg = f"- [{os.getenv('ENV')}] Candlestick pattern <strong>{status}</strong> #{symbol} \n - SD {sd} \n - Chaikin oscillator {value}, diff {'positive' if chaikin_diff >= 0 else 'negative'} \n - Regression line {regression} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots/new{symbol}"
        _send_msg(msg)
        print(msg)

        run_autotrade(symbol, ws, "candlestick_patterns")
    pass