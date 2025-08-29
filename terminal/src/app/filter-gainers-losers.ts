import { useMemo } from "react";
import { useGainerLosersQuery } from "../features/binanceApiSlice";
import { useGetSymbolsQuery } from "../features/symbolsApiSlice";

// Memoized hook to get filtered gainer losers based on VITE_TICKER_25
export function useFilteredGainerLosers() {
  const { data: gainerLosers = [], isLoading: loadingGL } = useGainerLosersQuery();
  const { data: apiSymbols = [], isLoading: loadingSymbols } = useGetSymbolsQuery();
    const combined = useMemo(() => {
    const symbolMap = new Map(apiSymbols.map(sym => [sym.id, sym]));
    return gainerLosers
      .filter(gl => symbolMap.has(gl.symbol))
      .map(gl => ({
        ...gl,
        apiSymbol: symbolMap.get(gl.symbol),
      }));
  }, [gainerLosers, apiSymbols]);

  // isLoading is true if either is true
  const isLoading = loadingGL || loadingSymbols;

  return { combined, isLoading };
}
