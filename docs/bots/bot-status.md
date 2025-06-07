# Bot status
Currently there are 5 status:
Active, inactive, error, complete, closed, archive
These are the values of the `status` property of the bot.

## Active bot
Indicates that the bot is actively trading. It must include data in the `deal` property which contain the prices that the bot is currenly trading, at least bought price (buy_price) and price to be sold e.g. take_profit, trailling profit.

An active bot cannot update the deal, because this relies on orders, and orders have already been executed.
Although it is allowed to "Save" again, but this relies on the research app and the websocket to trigger the change in market_updates

## Inactive bot
Indicates the bot is not currently trading. This usually happens when the bot is created, saved but no deal is opened.

## Closed bot
Bot has been manually closed. If performed correctly, it should have sold all cryptos under that market, and hedged. 

E.g. 
1. BNBBTC bot, clicked close.
2. BNB is sold, any active orders closed 
3. now balance adds BTC, 
4. BTC is sold again and converted into GBP.

If at any stage it fails to perform one the operations, errors will be appended into the bot `errors` property and status should be changed to `error`

## Error bot
During active, closing, completion, if the bot failed to do any operation, there will be errors listed under the `errors` property, and this status will be added.

## Completed bot
The bot successfully performed all of the actions without errors and closed.

## Archived bot
This status exists to unclutter the view. Bots only become archive if the user manually archives them. They will not show by default in the list of bots. They are stored for historical reference/analyses.
