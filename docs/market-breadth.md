# Market breadth

Market breadth pertains to self.market_breadth sections in Binquant.

The main concept of market breadth in Binbot is calculating advancers (gainers) and decliners (losers) differences, which creates a measure called ADP (advancers/decliners proportion). This ranges from -1 to +1 and classifies assets by their rolling 24-hour price change in the configured fiat market.

In my research, I've found out that although most assets do have a positive correlation with BTC, it's not always the case. To find out more you can query the btc-correlation endpoint.

## Cumulative net breadth

The breadth cron records a sample every 15 minutes, but its ADP value still uses
each asset's rolling 24-hour change. The 24-hour change is a speed, not a
position: when the 24-hour comparison point moves, a contract that keeps rising
can show a smaller 24-hour change and look like it fell.

For KuCoin futures, the same ingest also stores prices and 24-hour turnover for
the active contracts. For each breadth snapshot, the market-breadth response
compares every contract's price with the stored price snapshot 15 minutes
earlier (within five minutes). A contract is a gainer if its price rose and a
loser if it fell. The step value is

    (weight of gainers - weight of losers) / total weight * 100

on a -100..+100 scale. Each contract weighs the square root of its 24-hour
turnover. Liquid contracts count more, but BTC and ETH cannot dominate: with
full turnover weight, BTC and ETH alone were about 28% of the weight and the top
ten contracts about 52%. Turnover is only a weight; the difference between two
rolling 24-hour turnover values is not the volume of a 15-minute step.

`cumulative_breadth` is the running total of the steps, starting at the oldest
snapshot in the response. The steps do not overlap, so each move counts once:
noise cancels out and persistent breadth adds up. Read it like a price chart:
its direction is the trend, its level has no meaning. `cumulative_breadth_ema`
is its EMA over 16 samples (four hours). Missing steps are `null`, and the total
and its EMA carry over them. Price samples are retained for 36 hours, which
covers the dashboard's 100-point chart.

Earlier versions plotted the net breadth level itself, over 15-minute and then
one-hour windows. Crypto contracts move together with BTC, so the level was
mostly BTC's direction (beyond ±50 most of the time) and crossed zero about as
often as BTC's own one-hour return. Only the running total showed a trend.

The 24-hour breadth, its EMA trend, and the strength index remain in the
database and API response. The dashboard plots only the cumulative breadth and
its EMA.

## History

In the past, this was born out of the concept of gainers and losers of the day. Some assets that have a price percentage change in the last 24 hrs that is positive could, by the end of the day, be negative and this can show a clear market trend.

Previously, we uses the proportion of gainers vs losers and if former was bigger than the latter, then we declared a bullyish market, and vice versa. This is not a useful concept, because bullyish markets, which are the determinants of positive (or negative for short positions) percentage increases started much earlier. For example, the market could open early in the day in negative numbers (overwhemingly more losers than gainers), but then in an a hour or so, there could be signs of bullyish markets (assets percentage price changes go from -3% to -1%), this is when we want to trigger the bots to maximize gains, not when proportion of gainers is larger than losers. That's why it was re-coined as market breadth and logic was all changed.
