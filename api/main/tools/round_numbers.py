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
  return result

def proper_round(num, dec=6):
    num = str(num)[:str(num).index('.')+dec+2]
    if num[-1]>='5':
        return float(num[:-2-(not dec)]+str(int(num[-2-(not dec)])+1))
    return float(num[:-1])