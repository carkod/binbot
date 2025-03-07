---
layout: default
title: Home
description: "Homepage"
nav_order: 1
permalink: /
---

# Index
- [To Develop](#to-develop)
- [Concept](#concept)
  - [Filter](#filter)
  - [Use volatility](#use-volatility)
  - [Reassure trend](#reassure-trend)
  - [Look for buy and sell signals](#look-for-buy-and-sell-signals)
- [Sudden increase Algorithm](#sudden-increase-algorithm)
  - [Filters](#a-filters)
  - [Orders](#b-orders)
- [Autotrade](autotrade.md)
- [Account](account/)
  - [Bot](account/bot.md)
  - [Bot Status](account/bot-status.md)
  - [Paper Trading](account/paper-trading.md)
  - [Margin](account/margin.md)
  - [Hedging](account/hedging.md)
  - [Bot Strategies](account/bot-strategies.md)
- [Research](research/)
  - [QFL Signals](research/qfl_signals.md)
- [About Back-testing](about-backtesting.md)
- [Symbol Table vs Candlesticks](symbol-table-vs-candlesticks.md)
- [Rest API Standards](rest.md)
- [Reducers](reducers.md)
- [Klines](klines.md)
- [Deployment](deployment.md)
- [Code Styling](code-styling.md)
- [Binance Teapot Errors](binance-teapot-errors.md)
- [Architecture](architecture.md)
- [APIs](apis.md)
- [Why Not Use Chart.js](why-not-use-chartjs.md)
- [Webserver Issues](webserver-issues.md)
- [Tests Types](tests-types.md)

PLOTTING DOES NOT WORK WITH DEBUGGER

## To Develop

- Get list of crypto currencies in funds
- run sell algo with this list
- functionality on increasing intervals



## Concept
1. Filter:
    - Filter out coins > 10
    - Set BNB as the main market
    - Volume (to be determined)
2. Use volatility (Bollinger, Keltner channels) to determine change of trend
    - Higher volatility implies strength of move
    - Higher volatility implies trend as opposed to sideways move
    - Repeated green candlesticks surpassing top band
    
    
3. Reassure trend using DMI
4. Look for buy and sell signals with KST


## Sudden increase Algorithm

### A. Filters

Buy Filters:
0. Check positions (do I have BNB to buy?)
0. Monitor markets using ticker24:
1. Filter out coins > 10
1. > Certain volume 
1. Repeated green candlesticks surpassing top band => check it is not sideways move (DMI),
    if sideways move return false
    if trend checked return true
    
2. Check KST for buy signals. 
    if buy signal, check consistency in Bollinger/Keltner.
        if consistency fails return false
        if consistency true

3. Classify all TRUE (consistent coins) => choose highest potential increase
    for Algorithm testing, send emails
4. Buy 50% (for now)

### B. Orders

- Types of orders: limit order, market order, stop limit...  
    Need to make sure order executes
- Buy / sell order
