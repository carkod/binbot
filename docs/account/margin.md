# Margin trading

Margin trading is a concept from Binance. It essentially means, we are doing spot transactions with leverage. This leverage is given by Binance with an interest, you can borrow cryptoassets to open long or short positions. This type of trading, requires a different account on Binance, which as a consequence, requires fiat or crypto to be transfered from SPOT account to MARGIN account (these are the values in the Binance API), therefore, something to notice is that **you can't trade with SPOT account balance** you must have balance in the margin account.

## Binbot margin trading

> Note: "MARGIN" (uppercase) will be used in this document to refer to Binance MARGIN account, and "margin" or "Margin" (lowercase) will be used to talk about margin in general and margin in Binbot. Which is actually what the Binance API uses.

At the time of writing, margin denoted as `margin_long` `margin_short` in the bot strategy field, is limited by this restriction on Binance. The plan is to completely move all funds to MARGIN account and use the entire system on MARGIN balance.

The reason behind this decision is because with MARGIN account, you can trade both SPOT and MARGIN, while with SPOT, you can only trade SPOT. The main difference in terms of usage in Binbot, is that margin uses leverage (borrowing), so you can entirely skip leverage if uneeded in the current market conditions.

As a result, the Binbot Margin functionality is simply a switch of `long` and `short` strategy with the option of leverage. Here is an example (at time of writing, still WIP):

- `margin_long`: we want to buy BTCUSDT at 16,000 USDT. 
  1. We have the option to borrow (MARGIN) 16,000 USDT; or borrow a portion 10,000 USDT and use 6,000 USDT MARGIN balance; or only use balance.
  2. We buy BTC with USDT.
  3. We sell BTC in the future, at higher price.
  4. Binbot should automatically liquidate the loan right after selling to avoid accumulation of interest payments.

- `margin_short`: this would be like short-selling. Similarly, we want to buy BTCUSDT at 16,000 USDT
  1. We borrow (MARGIN) 1 BTC at current price 16,000 USDT
  2. We sell 1 BTC in the future, at lower price.
  3. Binbot should automatically liquidate the loan after selling and obtain

This strategy will allow us to cover both bullying (upward) and bearing (downward) market trends.
