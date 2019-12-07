import math

def round_numbers(value, decimals=6):
  decimal_points = 10 ** int(decimals)
  number = float(value)
  result = math.floor(number * decimal_points) / decimal_points
  return result
