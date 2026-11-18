import { createContext, useContext } from "react";
import type { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import type { useOrderBookHistory } from "./useOrderBookHistory";

interface MicrostructureData {
  symbol: string;
  selectSymbol: (symbol: string) => void;
  liquidity: ReturnType<typeof useFuturesLiquidityQuery>;
  orderBookHistory: ReturnType<typeof useOrderBookHistory>;
}

export const MicrostructureContext = createContext<
  MicrostructureData | undefined
>(undefined);

export const useMicrostructureData = () => {
  const data = useContext(MicrostructureContext);

  if (!data) throw new Error("MicrostructureProvider is required");
  return data;
};
