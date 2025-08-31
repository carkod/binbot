import { useMemo } from "react";
import { useGainerLosersQuery } from "./binanceApiSlice";

// Memoized hook to get filtered gainer losers based on VITE_TICKER_25
export function useFilteredGainerLosers() {
  const { data: gainerLosers = [] } = useGainerLosersQuery();
  const ticker25 = useMemo(
    () => (import.meta.env.VITE_TICKER_25 || "").split(","),
    [],
  );
  const filtered = useMemo(
    () => gainerLosers.filter((item) => ticker25.includes(item.symbol)),
    [gainerLosers, ticker25],
  );
  return filtered;
}
