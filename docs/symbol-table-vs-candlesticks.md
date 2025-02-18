
# Symbol table (API DB) vs Candlesticks (kline data from MongoDB)

Symbol table and stored candlesticks use different symbols because the data of symbol table come from the exchange info endpoint, which lists all of the available symbols, then they are filtered according to the fiat used by Binbot (at time of writing it's USDC). Candlestick data at the time of writing is about 127 vs 154 symbols in symbol table. There can be many reasons I haven't looked into, which include whether they are actively being traded in the exchange or not.

Work can be done to figure out the differences, but it's not necessarily desirable. These two data sources have to remain separate because:

1. Candlestick should stay clean and faithful to the candlestick format, otherwise we may have data corruption issues
2. **Nature of data is different**. Candlestick are high frequency, symbol name remains the same but other fields change constantly at high rate. Symbol data change very infrequently and they are dependant on exchange data, not market data.
3. Exchange info data has high weight on Binance. Polling constantly could ban us from requesting more data. However, websockets streams for candlestick data is meant to be requested every X minutes.