import { useMemo } from "react";
import { useGainerLosersQuery } from "../features/binanceApiSlice";
import { useGetSymbolsQuery } from "../features/symbolsApiSlice";
import { useFuturesRankingsQuery } from "../features/kucoinApiSlice";
import { normalizePriceChangePercent } from "../utils/gainers-losers";

// Memoized hook to get filtered gainer losers based on VITE_TICKER_25
export function useFilteredGainerLosers() {
  const { data: gainerLosers = [], isLoading: loadingGL } =
    useGainerLosersQuery();
  const { data: apiSymbols = [], isLoading: loadingSymbols } =
    useGetSymbolsQuery();

  const { data: futuresRankings = [], isLoading: loadingFutures } =
    useFuturesRankingsQuery();
  const combined = useMemo(() => {
    const symbolMap = new Map(apiSymbols.map((sym) => [sym.id, sym]));
    return gainerLosers
      .filter((gl) => symbolMap.has(gl.symbol))
      .map((gl) => ({
        ...gl,
        priceChangePercent: normalizePriceChangePercent(gl),
        apiSymbol: symbolMap.get(gl.symbol),
      }));
  }, [gainerLosers, apiSymbols, futuresRankings]);

  // isLoading is true if either is true
  const isLoading = loadingGL || loadingSymbols;

  return { combined, isLoading, futuresRankings, loadingFutures };
}

export function useFilteredFuturesRankings() {
  const { data: apiSymbols = [], isLoading: loadingSymbols } =
    useGetSymbolsQuery();

  const { data: futuresRankings = [], isLoading: loadingFutures } =
    useFuturesRankingsQuery();
  const combined = useMemo(() => {
    const symbolMap = new Map(apiSymbols.map((sym) => [sym.id, sym]));
    return futuresRankings
      .filter((fr) => symbolMap.has(fr.symbol))
      .map((fr) => ({
        ...fr,
        priceChangePercent: normalizePriceChangePercent(fr),
        apiSymbol: symbolMap.get(fr.symbol),
      }));
  }, [apiSymbols, futuresRankings]);

  // isLoading is true if either is true
  const isLoading = loadingSymbols || loadingFutures;

  return { combined, isLoading };
}
