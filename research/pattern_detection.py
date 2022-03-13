import talib
import numpy

# Except morning star and engulfing - these are pattern confirmations
patterns = {
    "CDL2CROWS": "Two Crows",
    "CDL3BLACKCROWS": "Three Black Crows",
    "CDL3INSIDE": "Three Inside Up/Down",
    "CDL3LINESTRIKE": "Three-Line Strike",
    "CDL3OUTSIDE": "Three Outside Up/Down",
    "CDL3STARSINSOUTH": "Three Stars In The South",
    "CDL3WHITESOLDIERS": "Three Advancing White Soldiers",
    "CDLABANDONEDBABY": "Abandoned Baby",
    "CDLADVANCEBLOCK": "Advance Block",
    "CDLBELTHOLD": "Belt-hold",
    "CDLBREAKAWAY": "Breakaway",
    "CDLCLOSINGMARUBOZU": "Closing Marubozu",
    "CDLCONCEALBABYSWALL": "Concealing Baby Swallow",
    "CDLCOUNTERATTACK": "Counterattack",
    "CDLDARKCLOUDCOVER": "Dark Cloud Cover",
    "CDLEVENINGSTAR": "Evening Star",
    "CDLGAPSIDESIDEWHITE": "Up/Down-gap side-by-side white lines",
    "CDLGRAVESTONEDOJI": "Gravestone Doji",
    "CDLHANGINGMAN": "Hanging Man",
    "CDLHARAMI": "Harami Pattern",
    "CDLHARAMICROSS": "Harami Cross Pattern",
    "CDLHIGHWAVE": "High-Wave Candle",
    "CDLHIKKAKE": "Hikkake Pattern",
    "CDLHIKKAKEMOD": "Modified Hikkake Pattern",
    "CDLHOMINGPIGEON": "Homing Pigeon",
    "CDLIDENTICAL3CROWS": "Identical Three Crows",
    "CDLINNECK": "In-Neck Pattern",
    "CDLKICKING": "Kicking",
    "CDLKICKINGBYLENGTH": "Kicking - bull/bear determined by the longer marubozu",
    "CDLLADDERBOTTOM": "Ladder Bottom",
    "CDLLONGLEGGEDDOJI": "Long Legged Doji",
    "CDLMARUBOZU": "Marubozu",
    "CDLMATHOLD": "Mat Hold",
    "CDLONNECK": "On-Neck Pattern",
    "CDLPIERCING": "Piercing Pattern",
    "CDLRICKSHAWMAN": "Rickshaw Man",
    "CDLRISEFALL3METHODS": "Rising/Falling Three Methods",
    "CDLSHOOTINGSTAR": "Shooting Star",
    "CDLSPINNINGTOP": "Spinning Top",
    "CDLSTALLEDPATTERN": "Stalled Pattern",
    "CDLSTICKSANDWICH": "Stick Sandwich",
    "CDLTAKURI": "Takuri (Dragonfly Doji with very long lower shadow)",
    "CDLTASUKIGAP": "Tasuki Gap",
    "CDLTHRUSTING": "Thrusting Pattern",
    "CDLTRISTAR": "Tristar Pattern",
    "CDLUNIQUE3RIVER": "Unique 3 River",
    "CDLUPSIDEGAP2CROWS": "Upside Gap Two Crows",
    "CDLXSIDEGAP3METHODS": "Upside/Downside Gap Three Methods",
}

reversal_patterns = {
    "CDLSHORTLINE": "Short Line Candle",
    "CDLLONGLINE": "Long Line Candle",
    "CDLDOJI": "Doji",
    "CDLDOJISTAR": "Doji Star",
    "CDLDRAGONFLYDOJI": "Dragonfly Doji",
    "CDLEVENINGDOJISTAR": "Evening Doji Star",
    "CDLHAMMER": "Hammer",
    "CDLINVERTEDHAMMER": "Inverted Hammer",
    "CDLSEPARATINGLINES": "Separating Lines",
    "CDLMATCHINGLOW": "Matching Low",
}


def reversal_signals(data):
    """
    Reversal signals that still require confirmation
    """
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    short_line = talib.CDLSHORTLINE(open=open, high=high, low=low, close=close)
    sl_check = bool(numpy.any(short_line[-10:-3]))

    long_line = talib.CDLLONGLINE(open=open, high=high, low=low, close=close)
    ll_check = bool(numpy.any(long_line[-10:-3]))

    hammer = talib.CDLHAMMER(open=open, high=high, low=low, close=close)
    hammer_check = bool(numpy.any(hammer[-5:]))
    
    return sl_check, ll_check, hammer_check

def reversal_confirmation(data):
    # Detect morning star pattern (price reversal)
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    morning_doji_star = talib.CDLMORNINGDOJISTAR(open=open, high=high, low=low, close=close)
    mds_check = bool(numpy.any(morning_doji_star[-10:]))

    morning_star_detection = talib.CDLMORNINGSTAR(open=open, high=high, low=low, close=close)
    ms_check = bool(numpy.any(morning_star_detection[-10:]))

    # Reversal confirmation
    engulfing_detection = talib.CDLENGULFING(open=open, high=high, low=low, close=close)
    e_check = bool(numpy.any(engulfing_detection[-10:]))

    return (ms_check or mds_check) and e_check

def reversal_pattern_recognition(data):
    """
    Detect all patterns, not just reversal
    """
    # Detect morning star pattern (price reversal)
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    detected_patterns = []

    for pattern in reversal_patterns:
        pattern_function = getattr(talib, pattern)
        results = pattern_function(open, high, low, close)
        if results[len(results) - 1] > 0:
            detected_patterns.append(reversal_patterns[pattern])

    return detected_patterns

def test_pattern_recognition(data):
    """
    Detect all patterns, not just reversal
    """
    # Detect morning star pattern (price reversal)
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    detected_patterns = []

    for pattern in reversal_patterns:
        pattern_function = getattr(talib, pattern)
        results = pattern_function(open, high, low, close)
        if results[len(results) - 1] > 0:
            detected_patterns.append(reversal_patterns[pattern])

    return detected_patterns
