# Market breadth

Market breadth pertains to self.market_breadth sections in Binquant.

The main concept of market breadth in Binbot is calculating advancers (gainers) and decliners (losers) differences, which creates a measure called ADP (advancers/decliners porportion). This is a number 0 - 1 (could also be turned into a percentage by multiplying to 100, but it's mathematically unecessary) that indicates the trend of the prices in a given market. At the time of writing, we are only using USDC market.

In my research, I've found out that although most assets do have a positive correlation with BTC, it's not always the case. To find out more you can query the btc-correlation endpoint.

## History

In the past, this was born out of the concept of gainers and losers of the day. Some assets that have a price percentage change in the last 24 hrs that is positive could, by the end of the day, be negative and this can show a clear market trend.

Previously, we uses the proportion of gainers vs losers and if former was bigger than the latter, then we declared a bullyish market, and vice versa. This is not a useful concept, because bullyish markets, which are the determinants of positive (or negative for short positions) percentage increases started much earlier. For example, the market could open early in the day in negative numbers (overwhemingly more losers than gainers), but then in an a hour or so, there could be signs of bullyish markets (assets percentage price changes go from -3% to -1%), this is when we want to trigger the bots to maximize gains, not when proportion of gainers is larger than losers. That's why it was re-coined as market breadth and logic was all changed.
