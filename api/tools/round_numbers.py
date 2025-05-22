import math
import re
from decimal import Decimal
from datetime import datetime


def supress_trailling(value: str | float | int) -> float:
    """
    Supress trilling 0s
    this function will not round the number
    e.g. 3.140, 3.140000004

    also supress scientific notation
    e.g. 2.05-5
    """
    value = float(value)
    # supress scientific notation
    number = float(f"{value:f}")
    number = float("{0:g}".format(number))
    return number


def round_numbers(value: float | int, decimals=6) -> float | int:
    decimal_points = 10 ** int(decimals)
    number = float(value)
    result = math.floor(number * decimal_points) / decimal_points
    if decimals == 0:
        result = int(result)
    return result


def round_numbers_ceiling(value, decimals=6):
    decimal_points = 10 ** int(decimals)
    number = float(value)
    result = math.ceil(number * decimal_points) / decimal_points
    if decimals == 0:
        result = int(result)
    return float(result)


def supress_notation(num: float, precision: int = 0) -> str:
    """
    Supress scientific notation
    e.g. 8e-5 = "0.00008"
    """
    dec_num = float(num)
    num = round_numbers(dec_num, precision)
    if precision >= 0:
        decimal_points = precision
    else:
        decimal_points = int(Decimal(str(num)).as_tuple().exponent * -1)
    return f"{num:.{decimal_points}f}"


def interval_to_millisecs(interval: str) -> int:
    time, notation = re.findall(r"[A-Za-z]+|\d+", interval)
    if notation == "m":
        # minutes
        return int(time) * 60 * 1000

    if notation == "h":
        # hours
        return int(time) * 60 * 60 * 1000

    if notation == "d":
        # day
        return int(time) * 24 * 60 * 60 * 1000

    if notation == "w":
        # weeks
        return int(time) * 5 * 24 * 60 * 60 * 1000

    if notation == "M":
        # month
        return int(time) * 30 * 24 * 60 * 60 * 1000

    return 0


def format_ts(time: datetime) -> str:
    """
    Central place to format datetime
    to human-readable date
    """
    return time.strftime("%Y-%m-%d %H:%M:%S.%f")


def zero_remainder(x):
    number = x

    while True:
        if number % x == 0:
            return number
        else:
            number += x


def round_timestamp(ts: int | float) -> int:
    """
    Round millisecond timestamps to always 13 digits
    this is the universal format that JS and Python accept
    """
    digits = int(math.log10(ts)) + 1
    if digits > 13:
        decimals = digits - 13
        multiplier = 10**decimals
        return int(round_numbers(ts * multiplier, decimals))
    else:
        return int(ts)


def ts_to_day(ts: float | int) -> str:
    """
    Convert timestamp to date (day) format YYYY-MM-DD
    """
    digits = int(math.log10(ts)) + 1
    if digits >= 10:
        ts = ts // pow(10, digits - 10)
    else:
        ts = ts * pow(10, 10 - digits)

    dt_obj = datetime.fromtimestamp(ts)
    b_str_date = datetime.strftime(dt_obj, "%Y-%m-%d")
    return b_str_date


def ms_to_sec(ms: int) -> int:
    """
    JavaScript needs 13 digits (milliseconds)
    for new Date() to parse timestamps
    correctly
    """
    return ms // 1000


def sec_to_ms(sec: int) -> int:
    """
    Python datetime needs 10 digits (seconds)
    to parse dates correctly from timestamps
    """
    return sec * 1000


def ts_to_humandate(ts: int) -> str:
    """
    Convert timestamp to human-readable date
    """
    if len(str(abs(1747852851106))) > 10:
        # if timestamp is in milliseconds
        ts = ts // 1000
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
