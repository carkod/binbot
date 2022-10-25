---
layout: default
title:  Autotrade
---

# Autotrade

## Restrictions
- Autotrade doesn't work with fiat currencies at the moment. It assumes GBP as main conversion fiat and uses it for hedging, but apart from that, Binance also allows trading with currencies such as Australian dollar (AUD), American dollar (USD), CNY (Chinese yuan) etc... which are skipped in the algo (research/__init__.py, skipped_fiat_currencies) on top of the blacklist cryptocurrencies, which are more specific cases.
- Autotrade checks for global settings from research_controller
- Autotrade checks for availability of balance
- Autotrade checks for existent active bots, to avoid creating the same bot


## default_5_so

Default percentage deviation of -5% safety orders with 5 safety orders.

This will create 5 safety orders that will trigger a BUY in when the price drops 5%.
Each safety order is set to increase the BUY quantity exponentially by 1.2,
starting from 10 USDT, which roughly will use up 172 USDT worth of funds.

Take for example, in the BTC/USDT market, give current price 20,000 USDT per BTC:

SO_1: Buy 10 USDT (qty) when price drops to @19,000 USDT per BTC
SO_2: 10^1.2 = 15.84 USDT (qty) when price drops to @18,050 (-5% drop)
SO_3: 15.84^1.2 = 27.52 USDT, when price drops to @17,147 (-5% drop)
...

1. Get total balance
2. Separate total balance evenly (exponentially increase)
3. Set buy price (-5% drop) and quantity (exponential 1.2 increase)


### Dynamic price_deviation

An update to include a dynamic price deviation was tested, it did not work well with candlestick_jump algorithm, because sudden movement in the markets do not change the volatility completely, therefore yielding a standard deviation which is quite low compared to the spread of the price.

As a result it created very tight, close safety orders, which is not useful as safety net for falling prices.

![Dynamic price deviation fail](./assets/dynamic-volatility-so.png)

Original code on autotrade.py -> activate_autotrade:

```python
if "sd" in kwargs:
    spread = ((kwargs["sd"] * 2) / self.default_bot["deal"]["buy_price"])
    self.default_bot["trailling_deviation"] = float(spread * 100)
        self.default_5_so(balances, base_order_price, per_deviation=(spread))
    else:
        self.default_5_so(balances, base_order_price)

```

However it is a good strategy for trailling profit.

Further research is required to do dynamic SOs