import os

def ma_candlestick_jump(close_price, open_price, ma_7, ma_100, ma_25, symbol, sd, value, chaikin_diff, regression, _send_msg, run_autotrade, ws, intercept):
    """
    Candlesticks are in an upward trending motion for several periods
    This algorithm checks last close prices > MAs to decide whether to trade

    Intercept: the larger the value, the higher the potential for growth
        e.g. Given predictor y = 0.123x + 2.5, for x = 1, y = 0.123 + 2.5 = 2.623
             Given predictor y = 0.123x + 10, for x = 1, y = 0.123 + 10 = 10.123

    Chaikin_diff: positive values indicate overbought, negative values indicate oversold
    - Buy when oversold, sell when overbought

    SD: standard deviation of 0.006 seems to be a good threshold after monitoring signals,
    whereas it is possible to get around 3% increase to actually make a profit
    """
    if (
        float(close_price) > float(open_price)
        and chaikin_diff < 0
        and sd > 0.006
        and float(intercept) > 10
        and close_price > ma_7[len(ma_7) - 1]
        and open_price > ma_7[len(ma_7) - 1]
        and ma_7[len(ma_7) - 1] > ma_7[len(ma_7) - 2]
        and close_price > ma_7[len(ma_7) - 2]
        and open_price > ma_7[len(ma_7) - 2]
        and close_price > ma_100[len(ma_100) - 1]
        and open_price > ma_100[len(ma_100) - 1]
        and close_price > ma_25[len(ma_25) - 1]
        and open_price > ma_25[len(ma_25) - 1]
    ):

        msg = f"- [{os.getenv('ENV')}] Candlesick <strong>jump algorithm</strong> {symbol} \n - SD {sd} \n - Chaikin oscillator {value}, diff {'positive' if chaikin_diff >= 0 else 'negative'} \n - Regression line {regression} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"
        _send_msg(msg)
        print(msg)

        run_autotrade(symbol, ws)
    
    return