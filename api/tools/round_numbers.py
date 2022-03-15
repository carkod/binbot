import math
from decimal import Decimal
import re

def round_numbers(value, decimals=6):
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
    return float(result)


def proper_round(num, dec=6):
    num = str(num)[: str(num).index(".") + dec + 2]
    if num[-1] >= "5":
        return float(num[: -2 - (not dec)] + str(int(num[-2 - (not dec)]) + 1))
    return float(num[:-1])


# Turn float string into float and prevent exponentialization
# 8f means 8 decimals - binance default
def floatify(string, decimals=6):
    fl = round_numbers(float(string), decimals)
    full_float = f"{fl:{decimals}f}"
    return full_float


def stringify_float(num, decimals=6):
    full_float = f"{num:{decimals}f}"
    return full_float


def supress_notation(num: float, precision: int = 0):
    """
    Supress scientific notation
    e.g. 8e-5 = "0.00008"
    """
    dec_num = float(num)
    num = round_numbers(dec_num, precision)
    if precision >= 0:
        decimal_points = precision
    else:
        decimal_points = Decimal(str(num)).as_tuple().exponent * -1
    return f"{num:.{decimal_points}f}"

def interval_to_millisecs(interval: str) -> int:
    time, notation = re.findall(r'[A-Za-z]+|\d+', interval)
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
