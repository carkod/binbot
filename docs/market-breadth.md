# Market breadth

Market breadth pertains to self.market_breadth sections in Binquant.

The main concept of market breadth in Binbot is calculating advancers (gainers) and decliners (losers) differences, which creates a measure called ADP (advancers/decliners proportion). This ranges from -1 to +1 and classifies assets by their rolling 24-hour price change in the configured fiat market.

In my research, I've found out that although most assets do have a positive correlation with BTC, it's not always the case. To find out more you can query the btc-correlation endpoint.

## Recent futures movement

The breadth cron records a sample every 15 minutes, but its ADP value still uses
each asset's rolling 24-hour change. An asset can fall over the last hour while
remaining positive over 24 hours, so ADP may remain high during a broad pullback.

For KuCoin futures, the same ingest also stores prices for the active contracts.
The market-breadth response compares each snapshot with the closest stored price
snapshot one and three hours earlier (within ten minutes). For contracts present
in both snapshots, it returns the median price return in percent and the share
with negative returns for each window. The four newest-first arrays are
`median_return_1h`, `median_return_3h`, `falling_share_1h`, and
`falling_share_3h`; missing comparisons are `null`. Price samples are retained
for 36 hours so the dashboard's 100-point chart can show these recent-return
lines alongside the existing 24-hour breadth and its EMA trend.

The strength index remains in the database and API response. The dashboard
plots the median 1-hour and 3-hour returns on a separate percent axis in its
place, and shows the latest falling shares above the chart. No additional
exchange request or table is needed.

## History

In the past, this was born out of the concept of gainers and losers of the day. Some assets that have a price percentage change in the last 24 hrs that is positive could, by the end of the day, be negative and this can show a clear market trend.

Previously, we uses the proportion of gainers vs losers and if former was bigger than the latter, then we declared a bullyish market, and vice versa. This is not a useful concept, because bullyish markets, which are the determinants of positive (or negative for short positions) percentage increases started much earlier. For example, the market could open early in the day in negative numbers (overwhemingly more losers than gainers), but then in an a hour or so, there could be signs of bullyish markets (assets percentage price changes go from -3% to -1%), this is when we want to trigger the bots to maximize gains, not when proportion of gainers is larger than losers. That's why it was re-coined as market breadth and logic was all changed.
