## Klines or candlesticks

Klines (Binance nomeclature) are candlestick charts that help us analyze market data and the evolution of prices, it is the main tool financial markets use to do trading or investment.

In this project, the Binance `/klines` endpoint is used to render the candlestick data in charts. So most of the function names that include "klines" refer to Binance data and functions that are named with "candlestick" refer to either internal candlestick data or transformed candlestick data using klines as a source.

Because of the recent changes in rate limit weights in this API endpoint on Binance's side, we are constantly banned or returned 418 status code when we try to constantly request data by the research application (/research), therefore I created an internal collection in the DB to store these candlestick datapoints. This internal DB usually updates using the websocket streams (/research/signals.py.start_stream), but if it finds gaps, the API `get_klines()` will automatically re-request data from the Binance API endpoint.