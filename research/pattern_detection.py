import talib
import numpy

def pattern_detection(data):
    # Detect morning star pattern (price reversal)
    open = numpy.asarray(data["open"], dtype='f8')
    high = numpy.asarray(data["high"], dtype='f8')
    low = numpy.asarray(data["low"], dtype='f8')
    close = numpy.asarray(data["close"], dtype='f8')

    morning_star_detection = talib.CDLMORNINGSTAR(open=open, high=high, low=low, close=close)
    ms_check = bool(numpy.any(morning_star_detection[-10:]))

    # Reversal confirmation
    engulfing_detection = talib.CDLENGULFING(open=open, high=high, low=low, close=close)
    e_check = bool(numpy.any(engulfing_detection[-10:]))

    return ms_check and e_check
