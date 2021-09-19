# Market Updates websockets connection

API Market Updates is a websocket class executes orders for bot deals, to open or close bots or specifically when to create or open the deals the bots manage.

Many options were explored before:
- Using simple REST endpoints didn't work, because market volatility favored sudden jumps and drops in prices, so a more real-time method like websockets is required to keep the data up to date
- Market update is a separate websocket from Order Updates, because Order updates requires USER DATA, while websockets such as kline does not need authentication. The format of the URI to listen to the websocket is different.
- `black_list` list exists to sych local against production databases. It can be removed in the future.

Limitations:
- At this point, Binance API does not seem to allow another way of getting updates for all market symbols. The other (websocket option)[https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#subscribe-to-a-stream] that uses subscription pattern allows to subscribe to different types of stream, it does not allow to receive multiple klines.
- Therefore, the only way it works is by subscribing to all streams at once, i.e. `/stream?streams=<streamName1>/<streamName2>/<streamName3>` or `/ws/<streamName>` as described in the (General WSS section)[https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#general-wss-information]
- Using a URIs that are too long would lead to a (414 error)[https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/414], therefore a loop was used to split it into multiple websocket connections
- Sometimes, new cryptos are released on Binance, therefore, MA signals analysis cannot be performed, there is an `if` condition to skip signals for such cases.
- Research vs API market updates are separated to increase current price updates. If updates don't come frequently enough (because there are too many cyrptocurrencies updating in a set interval of minutes or seconds) the window for optimal trading can be missed.

Perks:
- At /bots create and edit, the thread will access the websocket, close it, and restart it to get the new bots

# Research Market updates websocket connection

This research Market updates websocket connects, located `/research/__init__.py` aimed at creating telegram signals is a quite heavy websocket connection, that's why it has a separate python application:

- Hundreds of cryptcurrency markets are being listened to
- Only query string websocket channels seem to work with so many cyrptocurrencies (and counting) - This is due to the reasons mentioned in previous section.
- `self.max_request` variable added to avoid Request URI too long errors

## Telegram

The telegram bot uses the `telegram-python-bot` library, which is also internally a websocket. Therefore, when instance is created, it rises a conflict with existent websocket (`there can only be one instance of a bot` error) when the market_update websocket in on-going. That's why it's opened and then immediately closed after the message has been sent.

Because the Market Updates websocket happens continuously, it means the telegram bot will still be able to capture `/t <symbol>` messages.