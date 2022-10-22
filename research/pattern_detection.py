# import talib
# import numpy


# patterns don't really work so decomissioned

# Detecting the shape of two or three candles does not determine the entire trend
# ta-lib does not compile when installed in the dockerfile

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
    "CDLHOMINGPIGEON": "Homing Pigeon", # Too many false signals
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
    "CDLTASUKIGAP": "Tasuki Gap",
    "CDLTHRUSTING": "Thrusting Pattern",
    "CDLTRISTAR": "Tristar Pattern",
    "CDLUNIQUE3RIVER": "Unique 3 River",
    "CDLUPSIDEGAP2CROWS": "Upside Gap Two Crows",
    "CDLXSIDEGAP3METHODS": "Upside/Downside Gap Three Methods",
    "CDLTAKURI": "Takuri (Dragonfly Doji with very long lower shadow)", 
}

test_patterns = {
    "CDL2CROWS": "Two Crows",
    "CDL3BLACKCROWS": "Three Black Crows",
    "CDL3INSIDE": "Three Inside Up/Down",
    "CDL3LINESTRIKE": "Three-Line Strike",
    "CDL3STARSINSOUTH": "Three Stars In The South",
    "CDL3WHITESOLDIERS": "Three Advancing White Soldiers", # upward trend?
    "CDLABANDONEDBABY": "Abandoned Baby",
    "CDLADVANCEBLOCK": "Advance Block",
    "CDLBREAKAWAY": "Breakaway",
    "CDLCONCEALBABYSWALL": "Concealing Baby Swallow",
    "CDLCOUNTERATTACK": "Counterattack",
    "CDLDARKCLOUDCOVER": "Dark Cloud Cover",
    "CDLGAPSIDESIDEWHITE": "Up/Down-gap side-by-side white lines",
    "CDLHANGINGMAN": "Hanging Man",
    "CDLHIKKAKEMOD": "Modified Hikkake Pattern",
    "CDLIDENTICAL3CROWS": "Identical Three Crows",
    "CDLINNECK": "In-Neck Pattern",
    "CDLKICKING": "Kicking",
    "CDLKICKINGBYLENGTH": "Kicking - bull/bear determined by the longer marubozu",
    "CDLLADDERBOTTOM": "Ladder Bottom",
    "CDLMATHOLD": "Mat Hold",
    "CDLONNECK": "On-Neck Pattern",
    "CDLPIERCING": "Piercing Pattern",
    "CDLRISEFALL3METHODS": "Rising/Falling Three Methods",
    "CDLSHOOTINGSTAR": "Shooting Star",
    "CDLSTALLEDPATTERN": "Stalled Pattern",
    "CDLTASUKIGAP": "Tasuki Gap",
    "CDLTHRUSTING": "Thrusting Pattern",
    "CDLTRISTAR": "Tristar Pattern",
    "CDLUNIQUE3RIVER": "Unique 3 River",
    "CDLUPSIDEGAP2CROWS": "Upside Gap Two Crows",
}


def reversal_signals(data):
    """
    Reversal signals that still require confirmation
    """
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
        "CDLSPINNINGTOP": "Spinning Top",
        "CDLHIGHWAVE": "High-Wave Candle",
        "CDLRICKSHAWMAN": "Rickshaw Man",
        "CDLLONGLEGGEDDOJI": "Long Legged Doji",
        "CDL3OUTSIDE": "Three Outside Up/Down",
        "CDLSTICKSANDWICH": "Stick Sandwich",
    }

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

def reversal_confirmation(data):
    # Detect morning star pattern (price reversal)
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    morning_doji_star = talib.CDLMORNINGDOJISTAR(open=open, high=high, low=low, close=close)
    mds_check = bool(numpy.any(morning_doji_star[-3:]))

    morning_star_detection = talib.CDLMORNINGSTAR(open=open, high=high, low=low, close=close)
    ms_check = bool(numpy.any(morning_star_detection[-3:]))

    # Reversal confirmation
    engulfing_detection = talib.CDLENGULFING(open=open, high=high, low=low, close=close)
    e_check = bool(numpy.any(engulfing_detection[-3:]))

    return (ms_check) and e_check

def downtrend_patterns(data):
    """
    Downtrend patterns that I've found quite accurate
    """
    bearish_patterns = {
        "CDLHARAMI": "Harami Pattern",
        "CDLHARAMICROSS": "Harami Cross Pattern",
        "CDLHIKKAKE": "Hikkake Pattern",
        "CDLBELTHOLD": "Belt-hold",
        "CDLEVENINGSTAR": "Evening Star", # Possibly down reversal confirmation
        "CDLGRAVESTONEDOJI": "Gravestone Doji",
        "CDLTAKURI": "Takuri (Dragonfly Doji with very long lower shadow)",
    }
    
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    detected_patterns = []

    for pattern in bearish_patterns:
        pattern_function = getattr(talib, pattern)
        results = pattern_function(open, high, low, close)
        if results[len(results) - 1] > 0:
            detected_patterns.append(bearish_patterns[pattern])
    
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

    for pattern in test_patterns:
        pattern_function = getattr(talib, pattern)
        results = pattern_function(open, high, low, close)
        if results[len(results) - 1] > 0:
            detected_patterns.append(test_patterns[pattern])

    return detected_patterns


def chaikin_oscillator(data, volume):
    """
    On-balance volume.
    Describes trading volume https://www.investopedia.com/terms/o/onbalancevolume.asp
    @params
    data: Candlestick data (Open, High, Low, Close)
    @returns
    - check: boolean. True = positive chaikin, volume is on the up, False = negative chaikin, market 
    """
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')
    volume = numpy.asarray(volume, dtype='f8')

    real = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
    last_value = real[len(real) - 1]
    previous_last = real[len(real) - 2]
    return last_value - (previous_last), last_value

def linear_regression(data):
    """
    Create linear regression equation y = X1*x + Intercept
    The larger X1, the quicker prices are increasing, and viceversa
    Larger intercept means higher starting point
    Args:
    data: Candlestick data (Open, High, Low, Close)
    @returns
    string which contains an equation of the format y = X1x + i. Potentially can draw a graph
    """
    close = numpy.asarray(data["close"], dtype='f8')

    slope = talib.LINEARREG_SLOPE(close, timeperiod=25)
    intercept = talib.LINEARREG_INTERCEPT(close, timeperiod=25)
    last_slope = slope.tolist()[len(slope) - 1]
    last_intercept = intercept.tolist()[len(intercept) - 1]

    return last_slope, last_intercept

def stdev(data):
    """
    TA-lib returns 0.0 for a lot of data
    Use numpy std instead
    """

    close = numpy.asarray(data["close"], dtype='f8')

    standard_deviation = numpy.std(close)
    return standard_deviation
