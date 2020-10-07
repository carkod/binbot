 
import json
from main.account.models import Account
import os

 

class Balances:

  def __init__(self, app):
    self.key = os.getenv("BINANCE_KEY")
    self.secret = os.getenv("BINANCE_SECRET")
    self.base_url = os.getenv("BASE")
    self.order_url = os.getenv("TICKER24")

  def get_balances(self):
      data = json.loads(Account().get_balances().data)['data']
      available_balance = 0
      for i in range(len(data)):
          if data[i]['asset'] == 'BTC':
              available_balance = data[i]['free']
              return available_balance
      return available_balance
        
