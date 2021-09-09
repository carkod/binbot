# About Back-testing
Back testing is a strategy often used by algorithmic traders to test an algorithm before using it on real data.

I believe this is __not__ applicable in this system because:
- Cryptocurrency markets are highly volatile, predictions using past data are inaccurate.
- Previous data in charts never corresponds to a trend, a pattern or even normal distribution.

Therefore, this project focuses instead on forecasting based on present or near-present data, such as Moving Averages and Candlestick jumps. To provide more insight, I decrease the interval of the charts, to allow daily or hourly data taken into account, which serves as prediction for higher interval strategies, such as weekly or monthly trades.