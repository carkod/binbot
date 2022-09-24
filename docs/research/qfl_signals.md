## QFL Hodloo signals

File: research/qfl_signals.py, `on_message` method

The QFL signals uses the Quick finger Luke strategy, by buying in coin/tokens when the price goes down, thus reducing the average cost. It uses the Hodloo websocket service e.g. https://qft.hodloo.com/#/binance:btc-usdt, to get signals and after some analyses is performed, it sends an message to telegram and potentially an autotrade is triggered.

Most of the methods and functions in this file extend from the SetupSignals which is used in the main signals.py class.

At the time of writing, the code performs a basic screening of the coin/token: 

1. Grabs the relevant data, which are the base-break and panic signals, represented by a "bell" and a "x" respectively, in the Hodloo charts.
2. Filters out the leveraged tokens. These are probably the worst, as it can cause "cannibalism" (triggered one bot for BTCUSDT and then it could trigger another BTCDOWNUSDT which will eat each others profits), and most of the charts don't look so good in terms of trends.
3. **Key point**: Because of the relatively low amount of signals sent, it's been generalized to catch all signals except the leveraged tokens.
  - Even though the main platform we use is Binance, same pairs of coins/tokens are also present in other exchanges, therefore it could equally affect the market and potentially have similar if not the same signals to buy or sell.
  - Same with pairs. Even though the main market traded is USDT pairs, e.g. BTCBNB could equally affect the BTCUSDT market, therefore these are also relevant.
  - As a result, we could trade using "foreign" signals. More consistent research would be required to verify that this is not true.
  - Because of these reasons, we need to check crypto-compare (at this moment, this is the best free, not limited, low request weight API that we can use freely) to verify the existence of the pair, so that the autotrade does not break, because the signal doesn't exist. This avoids uncessary errors down the line.
