## Trailling profit
This should be the main strategy used for a bot.

When telgram bullying signal is received, open bot and set this trailling profit to a a small percentage (adjusted to the volatility of the market, so if spread is 10% then take profit or trailling profit should be about 5%), so that the deals are likely to complete.

The great thing about this strategy is that, if prices go up, we will not sell, we will keep tracking/trailling the prices until it bounces down. So the result is, we either make a high profit or a small profit.

- Bots using this feature, will have `trailling_stop_loss_price` set
- If prices reach take profit (which is set dynamically), API will switch on the `trailling_stop_loss_price` property, which means trailling has been activated, the take profit is no longer a fixed sell order, it becomes a moving "ceilling" that is used to set a stop loss when prices go down. This means that the bot will only sell and close on that trailling stop loss.

## Stop limit
Most of the time, stop limits (SL) should only be used to limit losses. If prices are likely to go up and then drop, use Trailling profit

## Safety orders
Use of safety orders (SO) is discouraged. 

If prices are likely to go up, it's always better to use a trailling order, because if after breaking the trailling take profit, the price takes a dip, it will automatically be sold at that new point.

If prices are likely to go down, then either not create a bot, use margin trading (not available at time of writing) or use safety orders if prices will bounce back for sure.

Another problem with SOs, is that a lot of balance is kept on hold. If SO deals are triggered only then balance will be used to cover that drop in prices, however if many bots use SOs, then this will easily drain balance available that could be used for other bots with more potential of price growth.

## Cooldown
Set time in seconds for a specific bot, to avoid immediately opening another bot right after completing one.


## Short strategy

`short_buy_price` and `short_sell_price` represent prices that are part of the short strategy. For more code information go to `/api/bots/schemas.py`

When prices fall too low, because of some kind of dip - a Bitcoin dip, an exchange collapse, or similar sort of event that causes all cryptocurrencies or a few to dip lower than historical prices, this will fall out of the catch of Safety orders. Safety orders are there only to catch bounces, but if a cryptocurrency falls 10% or 20%, then this short strategy will sell at `short_sell_price`, and buy again at `short_buy_price`.

As a result, `short_sell_price` must be lower than any safety orders, or there will be conflict triggering them.

A bot can `open_deal` on `short_buy_price` without a `short_sell_price`. An example scenario are the QFL signals, they sometimes emit **panic** signals which are downtrend charts. In such cases, we want to track the price down to a certain level where we believe it is the bottom, and then `short_buy` at reversal.