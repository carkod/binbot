from research.utils import supress_notation


"""
Signal algorithms that are inactive
"""

def candlestick_jump(symbol, close_price, open_price, data, telegram_bot):
    ma_100 = data["trace"][1]["y"]
    curr_candle_spread = float(data["curr_candle_spread"])
    curr_volume_spread = float(data["curr_volume_spread"])
    avg_candle_spread = float(data["avg_candle_spread"])
    avg_volume_spread = float(data["avg_volume_spread"])
    amplitude = float(data["amplitude"])
    all_time_low = float(data["all_time_low"])
    if (
        float(close_price) > float(open_price)
        and (
            curr_candle_spread > (avg_candle_spread * 2)
            and curr_volume_spread > avg_volume_spread
        )
        and (close_price > ma_100[len(ma_100) - 1])
        and amplitude > 0.1
    ):
        # Send Telegram
        msg = f"- Candlesick <strong>jump</strong> {symbol} \n- Amplitude {supress_notation(amplitude, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

        if close_price < float(all_time_low):
            msg = f"- Candlesick jump and all time high <strong>{symbol}</strong> \n- Amplitude {supress_notation(amplitude, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

        telegram_bot._send_msg(msg)
        print(msg)
