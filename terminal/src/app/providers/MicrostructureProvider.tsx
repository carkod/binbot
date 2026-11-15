import { useState, type ReactNode } from "react";
import { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import { OBI_POLL_INTERVAL_MS } from "../../features/kucoinLiquidity";
import { MicrostructureContext } from "../hooks/useMicrostructureData";
import { useKucoinTradeFlow } from "../hooks/useKucoinTradeFlow";
import { useOrderBookHistory } from "../hooks/useOrderBookHistory";

export const MicrostructureProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  // Keep the last bot symbol collecting across tabs and navigation.
  const [symbol, selectSymbol] = useState("");
  const liquidity = useFuturesLiquidityQuery(symbol, {
    skip: !symbol,
    pollingInterval: OBI_POLL_INTERVAL_MS,
    skipPollingIfUnfocused: false,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });
  const snapshot = liquidity.currentData;
  // A failed book refresh should not interrupt an already validated trade stream.
  const tradeFlow = useKucoinTradeFlow(
    symbol,
    Boolean(symbol && snapshot),
    snapshot?.multiplier,
  );
  const orderBookHistory = useOrderBookHistory(
    snapshot,
    Boolean(symbol),
    liquidity.isError,
    symbol,
  );

  return (
    <MicrostructureContext.Provider
      value={{ symbol, selectSymbol, liquidity, tradeFlow, orderBookHistory }}
    >
      {children}
    </MicrostructureContext.Provider>
  );
};
<<<<<<< HEAD
=======

export const MicrostructureProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  const routeSymbol =
    useMatch("/microstructure/:symbol?")?.params.symbol?.trim().toUpperCase() ||
    "";
  const [lastSymbol, setLastSymbol] = useState(routeSymbol);
  const symbol = routeSymbol || lastSymbol;

  useEffect(() => {
    if (routeSymbol) setLastSymbol(routeSymbol);
  }, [routeSymbol]);

  // Key the collector by symbol so returning to a route keeps the same stream,
  // while a new symbol disposes the previous stream and its order-book history.
  return (
    <MicrostructureCollector
      key={symbol}
      symbol={symbol}
      selectSymbol={setLastSymbol}
    >
      {children}
    </MicrostructureCollector>
  );
};
>>>>>>> 5f425392 (Remove unused binance clean up jobs)
