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
