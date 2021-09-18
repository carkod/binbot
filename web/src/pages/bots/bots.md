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