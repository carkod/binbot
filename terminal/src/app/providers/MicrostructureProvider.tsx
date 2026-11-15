import { useState, type ReactNode } from "react";
import { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import { OBI_POLL_INTERVAL_MS } from "../../features/kucoinLiquidity";
import { MicrostructureContext } from "../hooks/useMicrostructureData";
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
  const orderBookHistory = useOrderBookHistory(
    snapshot,
    Boolean(symbol),
    liquidity.isError,
    symbol,
  );

  return (
    <MicrostructureContext.Provider
      value={{ symbol, selectSymbol, liquidity, orderBookHistory }}
    >
      {children}
    </MicrostructureContext.Provider>
  );
};
