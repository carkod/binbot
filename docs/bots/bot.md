# About API `api/bots`

## Bot data
When working with bot data manipulation, the Python code will always use the Pydantic model BotModel.

However, to work with database, we need to adhere to the SQLAlchemy model, which is parsed using the SQLModel BotTable or PaperTradingTable. There is a utility method in BotModel which helps convert them.

BotModel creates consistency and it is the default way of FastAPI data guards. However, it does not work well with SQLAlchemy (I wish I could just use BotModel and store in the DB but that caused a lot of problems)


## Bot logs
The BotModel Pydantic Model has a field `logs` which is what we use to display milestone events in the bot's life. For example, when trailings are updated (trailing stop loss or trailling profits) or when an stop loss is executed or a take profit is executed.

These logs or event logs are specially helpful to debug the lifecycle of the bot, because if there's a bug and the streaming service is stuck somehow, you'll see that bot doesn't get updated for a long time, or if the market volume is so low that we don't receive price updates in a long time, first indication would be these logs (you may not even notice this in Grafana)

Each of these log messages have a timestamp automatically appended, to avoid duplicated work and convience for the developer. This comes in 3 flavors:
- the endpoint `/paper-trading/errors/` and `/bots/errors`. These are network requests, often used by services or external clients, *not to* be used by bintbot API internally for obvious reasons, you are calling the same host to make a log update. As an example, Binquant uses this and the terminal React app uses this too.
- self.controller.update_logs which is an independent database call, that pushes/appends the log message to the existing stack of messages. This is the default way to update event logs in a completely isolated way.
- most performant way is to use the `BotModel.add_log`, this is built-in to the BotModel pydantic model, but requires saving using `controller.save` which is a BotCrud method. If you are updating multiple logs multiple times, this can be the most performance way.


# Profit canibalization

## Context
To avoid one bot eating the profit of another bot, "Composite bot" feature was added and posteriorly removed. This is because if one bot is opened with certain parameters and another is opened with different parameters, they will remove/add cryptocurrencies and eventually break the strategy and most likely cause errors and losses. Also there is the possibility of eating each other's profit, if accidently one bot is opened for a down trend and another is opened for up trend.


## Pair uniqueness
Therefore, on the DB level, there is a restriction for **pair uniqueness** in `/app.py`. This means, there will never be a situation where bots are created using the samae pair.

This also helps avoid errors in websockets, where once a trailling or safety order closes, they will get "Invalid quantity" errors because the initial `bot["deal"]["buy_total_qty"]` does not match the available amount in the balance.


# Bot parameters

Create, Edit body

```
"pair": "", # Required
"status": "inactive", # inactive, active, completed
"name": "Default Bot",
"max_so_count": "3",
"balance_usage": "1",  # 100% of All Btc balance
"balance_size_to_use": "0.0001",  # qty of each so
"base_order_size": "0.003",  # MIN by Binance = 0.0001 BTC
"start_condition": "true",
"so_size": "0.0001",  # Top band
"take_profit": "0.003",
"price_deviation_so": "0.0063",  # % percentage
"trailling": "false",
"trailling_deviation": 0.0063,
"deal_min_value": 0,
"cooldown": 0,
"auto_strategy": "false", # Flip strategy automatically
"deals": [],
```


# About Dashboard `web/bots`

## Key function `computeAvailableBalance` for updating balance

- The function `this.props.getSymbolInfo(pair);` will trigger the API endpoint `/account/symbol/pair` to get exchange info of the specified `pair`
- Because `this.props.getSymbolInfo(pair)` is a dispatcher (notice the `this.props`), it will dispatch that API call, and trigger `componentDidUpdate()`
- `componentDidUpdate()` will check for changes in the props, and will trigger the `computeAvailableBalance()` and update the Available balance count.
- This is a centralized function, which is triggered by a number of events: changes in base order size, changes in strategy, changes in pair. they will all need to update the balance.
- Long strategies require the base asset (Binance term)
- Short strategies require the quote asset


## Internal vs User parameters

`deal` and `orders` are internal data used for the API to deal the bots
All other params can be set by the user

## Key function `computeAvailableBalance` for updating balance

- The function `this.props.getSymbolInfo(pair);` will trigger the API endpoint `/account/symbol/pair` to get exchange info of the specified `pair`
- Because `this.props.getSymbolInfo(pair)` is a dispatcher (notice the `this.props`), it will dispatch that API call, and trigger `componentDidUpdate()`
- `componentDidUpdate()` will check for changes in the props, and will trigger the `computeAvailableBalance()` and update the Available balance count.
- This is a centralized function, which is triggered by a number of events: changes in base order size, changes in strategy, changes in pair. they will all need to update the balance.
- Long strategies require the base asset (Binance term)
- Short strategies require the quote asset


## Internal vs User parameters

`deal` and `orders` are internal data used for the API to deal the bots
All other params can be set by the user

# FAQs

## Why simple "Save" is not allowed?
When a Bot is created and saved, we force it to activate so that it can check the feasibility of the strategy. Some checks like price, can only be performed when interacting with the API, as this is the matching engine's job to determine which price (limit or market) the bot should choose.

Therefore, once the bot is saved, the system will automatically assign a price to the bot to open the base and take profit positions. Once this is executed, and thus the bot is activated, changing any details in the form will be senseless, as these orders have already been executed. Only deactivating is allowed, so that details can be changed and then reactivate the order and open the deals again with the new parameters.

Note that deactivating the bot will close all orders currently ongoing.
## Why can't I choose a price to buy or sell?
A price to buy or sell cannot be chosen, because the matching engine takes care of this by pull data from market book prices and then choosing the best that matches the quantity allocated in the form.

## Why do I often get base order size error?
The base order size error is tightly coupled with available balance, as this is the main front-end controlled mechanism to prevent activating a bot that does not have enough funds. If this validation is removed, the Binance API will still complain of MIN NOTIONAL errors or similar.

## Why not use algo orders for take_profit and safety_orders (TAKE_PROFIT, STOP_LOSS)?
The Binance maximum is only 5 algo orders, which is not enough to make many orders.