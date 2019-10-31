import uuid

class Deal(Bot):

  def __init__(self, balance, spread):
    Bot.__init__(self, balance, spread, "long")