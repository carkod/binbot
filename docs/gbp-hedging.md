# GBP hedging `buy_gbp_balance` and `sell_gbp_balance`

## Why do we need GBP hedging?

Bitcoin (BTC) can be quite volatile at times. Sometimes it can drop -15% in a matter of weeks and after a month we could be incurring a huge loss, not because we are investing in BTC but because holding deposits are kept in BTC to trade in other cryptocurrencies.

This was one of the drawbacks of using third party bots such as 3Commas, where total earnings were going down despite bots making profits.

To avoid this side effect of using BTC or any other ALT coin which can equally be volatile, as the market often moves together with BTC, we take advantage of Binance's option to put money into real currencies.

Tether coins were also examined and deemed unsuitable to hedge, due to quick withdrawal issues (you are still holding a cryptocurrency).

The sterling pound was chosen (GBP) because currently I live in UK and it's the strongest currency in the world (other currencies that have higher value tend to not have a solid economy such as "the petrol economies" countries).

## How does it work?

GBP hedging in this project works by always keeping idle holdings (money waiting to be used) most of the time in GBP.

`sell_gbp_balance` function, currently inside of `Deal` class, is a standard sell asset function. Because Binance market is e.g. BTCGBP, this order performs a buy order, to get GBP.

`buy_gbp_balance` function, currently inside of `Deal` class, works with an additional parameter, which allows to switch between using the Deal base_order bought quantity, or using the entire market balance (e.g. whatever is available in BTC in the balance).
This is due to the deal orders quantities changing slightly because of the matching engine, and for hedging to work well, we need to make sure there is as much as possible in GBP.
By default, if not specified in the args, it will sell all market coin e.g. BTC in the balance, to hedge.
