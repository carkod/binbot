import uuid

class Bot:

  def __init__(self, balance, spread, botType="long"):
    self.id = uuid.uuid1()
    self.balance = balance
    self.spread = spread # Spread or Volatility or Standard devition (use Poobah One sheet)
    self.botType = botType
    self.binancePairName = 'BTCBNB'
    self.botName = 'Bot Name Example'
    self.baseOrderSize = '0.0000245'
    self.soSize = '0.33%' # Assuming 1% spread
    self.startCondition = bool(true) # True | False. Condition will be returned by external functions
    self.maxSOCount = 3 # fixed for now # Validation = MaxSOCount < Balance
    self.activatedSO = 2 # fixed for now
    self.SOpriceDeviation = spread / maxSOCount # Spread / # MaxSOCount
    self.dealMinVolume = 0
    self.coolDownTime = 3000 # Milliseconds (seconds in interface)
    self.amountUsedByBot = baseOrderSize + (soSize * maxSOCount)
    self.percentageAvailableForBot = '> 100%' if balance < amountUsedByBot else ((amountUsedByBot/balance) * 100) + '%'


  # def startDeal(self):
