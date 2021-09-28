# About `deal_updates`

The DealUpdates class in `deal_updates.py` is an "accompaniment" class for order_update and market_update web sockets. Because these two get real time updates and the code is similar, it was refactored into a shared group of functions, but it does not function independendently, it is only part of those two websockets programs.