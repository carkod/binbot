import math

def round_numbers(value, decimals=6):
    decimal_points = 10 ** int(decimals)
    number = float(value)
    result = math.floor(number * decimal_points) / decimal_points
    return result

def round_numbers_ceiling(value, decimals=6):
    decimal_points = 10 ** int(decimals)
    number = float(value)
    result = math.ceil(number * decimal_points) / decimal_points
    return float(result)

def proper_round(num, dec=6):
    num = str(num)[:str(num).index('.')+dec+2]
    if num[-1] >= '5':
        return float(num[:-2-(not dec)]+str(int(num[-2-(not dec)])+1))
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

def supress_notation(num: float):
    """
    Supress scientific notation
    e.g. 8e-5 = "0.00008"
    """
    return '%f' % (num)
