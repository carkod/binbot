import { useEffect, useState, type ReactNode } from "react";
import { useMatch } from "react-router";
import { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import { OBI_POLL_INTERVAL_MS } from "../../features/kucoinLiquidity";
import { MicrostructureContext } from "../hooks/useMicrostructureData";
import { useKucoinTradeFlow } from "../hooks/useKucoinTradeFlow";
import { useOrderBookHistory } from "../hooks/useOrderBookHistory";

const MicrostructureCollector = ({
  symbol,
  selectSymbol,
  children,
}: {
  symbol: string;
  selectSymbol: (symbol: string) => void;
  children: ReactNode;
}) => {
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

  // Hooks reset their data on symbol changes without remounting bot forms.
  // Returning to a route with the same symbol keeps the existing stream.
  return (
    <MicrostructureCollector symbol={symbol} selectSymbol={setLastSymbol}>
      {children}
    </MicrostructureCollector>
  );
};
