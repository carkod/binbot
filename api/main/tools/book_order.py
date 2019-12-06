import os
import requests
from main.tools import handle_error, EnumDefinitions
import pandas as pd

class Book_Order():

  def __init__(self, symbol, qty):
    self.key = os.getenv("BINANCE_KEY")
    self.secret = os.getenv("BINANCE_SECRET")
    self.base_url = os.getenv("BASE")
    self.order_url = os.getenv("ORDER")
    self.order_book_url = os.getenv("ORDER_BOOK")
    self.symbol = symbol
    self.quantity = qty


  """
  Buy order = bids
  Sell order = ask
  """
  def matching_engine(self, limit_index, order_side='bids'):
    url = self.base_url + self.order_book_url
    limit = EnumDefinitions.order_book_limits[limit_index]
    params = [
        ('symbol', self.symbol),
        ('limit', limit),
    ]
    res = requests.get(url=url, params=params)
    handle_error(res)
    data = res.json()
    if order_side == 'bids':
        df = pd.DataFrame(data['bids'], columns=['price', 'qty'])
    elif order_side == 'asks':
        df = pd.DataFrame(data['asks'], columns=['price', 'qty'])

    else:
        print('Incorrect bid/ask keyword for matching_engine')
        exit(1)

    df['qty'] = df['qty'].astype(float)

    # If quantity matches list
    match_qty = df[df['qty'] > float(self.quantity)]
    condition = df['qty'] > float(self.quantity)
    if condition.any() == False:
        limit += limit
        self.matching_engine(limit)

    return match_qty['price'][0]
