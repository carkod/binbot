## Klines or candlesticks

Klines (Binance nomeclature) are candlestick charts that help us analyze market data and the evolution of prices, it is the main tool financial markets use to do trading or investment.

In this project, the Binance `/klines` endpoint is used to render the candlestick data in charts. So most of the function names that include "klines" refer to Binance data and functions that are named with "candlestick" refer to either internal candlestick data or transformed candlestick data using klines as a source.

Because of the recent changes in rate limit weights in this API endpoint on Binance's side, we are constantly banned or returned 418 status code when we try to constantly request data by the research application (/research), therefore I created an internal collection in the DB to store these candlestick datapoints. This internal DB usually updates using the websocket streams (/research/signals.py.start_stream), but if it finds gaps, the API `get_klines()` will automatically re-request data from the Binance API endpoint.

These candlesticks are stored as '1m' intervals. Only storing it with the smallest interval, allows us to then aggregate into buckets (MongDB kafka db under kline collection) to create any other larger intervals (1 hour, 6 hours, 1 day, 1 week, 1 month...). Binance does offer even smaller intervals, which are probably the ones built up from book orders, but the througput can be too high, racking up server costs. At the moment, we don't need less than 1m, as we don't do high frequency trading.

### Grafana

There's a [Grafana dashboard](https://grafana.binbot.in/) to monitor these klines. Because servers can timeout, data may be inconsistently stored, but in theory, the websocket connection should persist 24/7 to store this data. It's crucial to keep it alive, as Binquant analytics relies on this.

To check these candlesticks go to:
1. Login into [Grafana dashboard](https://grafana.binbot.in/)
2. Got to "Dashboards" on the left navigation
3. Click on "Candlestick debug", should be the first item.
4. You'll be presented with a list of candlestick charts. If you can't find the pair/symbol you are looking for, create a new chart.

### Monitoring a chart

Pick the chart you are interesting in and check out for:
- The chart matches whatever you see on other sites that show candlesticks, ideally on Binance the shape should be exactly the same at the given interval (make sure you select the right interval in the "Refresh" dropdown)

- Check any missing datapoints (gaps). They look like missing candles in the chart.

Gaps are not something to be fixed. The way to deal with them is to investigate the underlying issue that caused it and fix it, instead of filling up the datapoint. sometimes there may be an error in the producer.py that caused it, and that simply needs to be fixed.
If the chart doesn't match at all what you see on Binance or other sites. There's a structural problem - the way candles are stored may be completely wrong or the symbol is wrong.

#### Create a new chart
1. Find an exisiting chart and click on the 3 dots on top right corner.
2. In the Queries tab, scroll down to the `grafana-mongodb-opensource-datasource` A query and copy the time serie query. It looks like somthing like this
```
db.kline.aggregate([
  {"$match": {"symbol": "SUIUSDC"}},
  {"$group":{
        "_id": {
           "time": {
                        "$dateTrunc": {
                            "date": "$close_time",
                            "unit": "minute",
                            "binSize": 15
                        },
                    },
        },
        "open": {"$first":"$open"},
        "close": {"$last":"$close"},
        "high": {"$max":"$high"},
        "low": {"$min":"$low"},
        "close_time": {"$last": "$close_time"},
        "open_time": {"$first": "$open_time"},
        "volume": {"$sum": "$volume"}
      }},
])
```
3. Go to Transformation tab and take a look at "convert field type". You'll have to replicate this in the new chart.
4. In your copied query, replace `symbol` with the symbol you want to monitor.
5. Create a new visualization by clicking on the "Edit" button at the top right, in the second navigation.
6. An "Add" button will appear now. Click it and click "Visualization".
7. Go to the right navigation and choose "Candlestick" in the dropdown.
6. Go to transformations tab and add a new transformation:
- For field select "close_time" as "Time" type and format `YYYY-MM-DD HH:mm:ss`
- Add another "convert field type" and do the same for "open_time"
7. Go to "panel options" on the right navigation and replace the "Panel title" with the name of the pair/symbol
8. Now you can save the dashboard.
