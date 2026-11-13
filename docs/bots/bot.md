# About API `api/bots`

## Bot data
When working with bot data manipulation, the Python code will always use the Pydantic model BotModel.

However, to work with database, we need to adhere to the SQLAlchemy model, which is parsed using the SQLModel BotTable. There is a utility method in BotModel which helps convert them.

BotModel creates consistency and it is the default way of FastAPI data guards. However, it does not work well with SQLAlchemy (I wish I could just use BotModel and store in the DB but that caused a lot of problems)


## Bot logs
The BotModel Pydantic Model has a field `logs` which is what we use to display milestone events in the bot's life. For example, when trailings are updated (trailing stop loss or trailling profits) or when an stop loss is executed or a take profit is executed.

These logs or event logs are specially helpful to debug the lifecycle of the bot, because if there's a bug and the streaming service is stuck somehow, you'll see that bot doesn't get updated for a long time, or if the market volume is so low that we don't receive price updates in a long time, first indication would be these logs (you may not even notice this in Grafana)

Each of these log messages have a timestamp automatically appended, to avoid duplicated work and convience for the developer. This comes in 3 flavors:
- the endpoint `/bot/errors`. These are network requests, often used by services or external clients, *not to* be used by bintbot API internally for obvious reasons, you are calling the same host to make a log update. As an example, Binquant uses this and the terminal React app uses this too.
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

## Conditional LIMIT entries (KuCoin futures)

In the dashboard, focusing the stop-loss, trailing-profit, trailing-deviation, or
conditional entry-price input unlocks its corresponding chart line. Dragging the
line updates the form; saving or updating the bot remains a separate action.
Trailing deviation is measured from the trailing-profit reference, while stop
loss and trailing profit are measured from the opening price (or conditional
entry price before opening). Clicking elsewhere or pressing Escape locks the line.
Submitted entry prices and completed bots cannot be dragged.
Live quotes are frozen as the preview reference while a field is selected, so
dropping a line and returning focus to the input preserves the selected price.

Focusing `entry_expires_at` shows a draggable magenta vertical expiry line for
an unsubmitted conditional entry. Moving it updates the local-time input and
expiry mark continuously; past expiry drops are rejected. Switching fields,
clicking elsewhere, pressing Escape, or selecting Immediate hides the handle.
Pending, active, completed, and already-submitted entries cannot edit expiry.
Pan to the future if the expiry is offscreen. The handle supports fixed-duration
timeframes (including the default hourly chart), with minute precision.

Conditional entries have a magenta price line and `E`/`X` timescale marks for
creation and expiry. Marks use the existing hourly timestamp format; TradingView
may not display an expiry mark until its timestamp is within the available bars.
These interactions require the accompanying `binbot-charts` library changes;
the published 0.16.4 package does not provide the drag callbacks or the
`timeMarker` / `onTimeMarkerMove` expiry API. Dashboard validation uses the local
charts build. Before deploying, publish the updated library and update the
dashboard dependency and lockfile; a clean install of 0.16.4 cannot run these
interactions.

Bots accept `entry_mode`: `immediate` (default) or `conditional_limit`. The shared
Pydantic model validates these values; the database stores a string. A conditional
entry requires a positive `entry_price`, which otherwise defaults to `null`.
The dashboard prefills it from the chart's current price and shows an editable
expiry six hours from selection, displayed in local time. `entry_expires_at` is an absolute Unix
millisecond timestamp, defaulting to `created_at + 21600000` (six hours). Omitted
or null mode/expiry values use those defaults.

Manual activation arms the bot as `pending` without submitting an order. Binquant
can create the same pending candidate directly. Streaming checks a fresh order
book: a long needs ask <= limit, a short needs bid >= limit. The limit is rounded
to the exchange tick without worsening the requested price. Conditional entries
never use strategy repricing or market fallback.

Conditional-entry failures are timestamped on the bot and appended to its stored
logs before the exception stops the attempt. Repeated identical failure messages
are suppressed during retries. Logging updates only the logs, preserving newer
position state. Deleted candidates retain their reason on the in-memory model
and in the activation response or streaming logs; they are never saved again just
to retain a log message.

Candidates compete for available futures funds and `max_active_autotrade_bots`.
Waiting conditional candidates do not occupy execution slots; active bots,
immediate pending entries, and submitted conditional entries do. The entry check
and submission are serialized across API/streaming processes using PostgreSQL.
A full bot limit leaves the candidate waiting until capacity becomes available or
it expires. Insufficient funds for the minimum contract sets the unsubmitted
candidate to `closed`, retaining its configuration and closure reason. Sizing
retains the existing affordable-contract clamp and fee-aware
margin check, so a candidate may open a smaller position than requested.

There are no entry groups and no automatic sibling cancellation. Several
candidates may open when both funds and execution slots permit. Other existing
positions remain managed normally.

The same absolute deadline covers waiting for the price and an unfilled submitted
order; submission does not restart the six-hour clock. Expired unsubmitted bots
are set to `closed`. Submitted entries are cancelled and reconciled, then the bot is closed
once no fills or position remain; fills found during cancellation become managed
positions instead. Uncertain submission outcomes
retain their client ID for reconciliation and are never closed as unfunded.

Closed candidates retain their IDs, signal links, deals, orders, entry configuration,
and logs for analysis. Bot GET endpoints exclude them by default, including
`status=all`. Use `GET /bot?status=closed` for archived candidates only, or
`include_closed=true` to include them in lists, ID/symbol lookups, and algorithm
rankings. They do not occupy active bot slots and cannot be reactivated.
The deadline stops governing the position after entry fills. Immediate strategies
retain their existing strategy-specific order timeouts.

The worker currently polls on its existing 15-second sweep; a brief touch can be
missed and reaching the price does not guarantee a fill. Entry configuration is
immutable after order submission. Deploy the updated shared pybinbot package and
apply the replay-safe entry migration before starting the updated services.

### Entry implementation and diagnostics

`ConditionalEntry` in `api/deals/conditional_entry.py` owns conditional arming, capacity
checks, explicit-price triggers and submission deadlines. Immediate entry stays
in `KucoinPositionDeal.base_order()`. Both paths import `submission_guard` from
`api/tools/utils.py` and share margin sizing, affordability validation and
client-order-ID recovery operations.
This keeps the conditional decision flow separate while preserving account-wide
serialization and exchange order identity.

Streaming stores unresolved-fill diagnostics in the bot's saved `logs`.
Conditional deletion reasons are added to the returned bot before deletion;
deleting the bot also removes its persisted logs. The worker does not save the
bot afterward.
