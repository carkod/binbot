import { useMemo } from "react";
import { useGainerLosersQuery } from "../../features/binanceApiSlice";
import { useFuturesRankingsQuery } from "../../features/kucoinApiSlice";
import { useGetSymbolsQuery } from "../../features/symbolsApiSlice";
import { normalizePriceChangePercent } from "../../utils/gainers-losers";

export function useFilteredGainerLosers() {
  const { data: gainerLosers = [], isLoading: loadingGL } =
    useGainerLosersQuery();
  const { data: apiSymbols = [], isLoading: loadingSymbols } =
    useGetSymbolsQuery();
  const { data: futuresRankings = [], isLoading: loadingFutures } =
    useFuturesRankingsQuery();

  const combined = useMemo(() => {
    const symbolMap = new Map(apiSymbols.map((symbol) => [symbol.id, symbol]));
    return gainerLosers
      .filter((gainerLoser) => symbolMap.has(gainerLoser.symbol))
      .map((gainerLoser) => ({
        ...gainerLoser,
        priceChangePercent: normalizePriceChangePercent(gainerLoser),
        apiSymbol: symbolMap.get(gainerLoser.symbol),
      }));
  }, [gainerLosers, apiSymbols]);

  return {
    combined,
    isLoading: loadingGL || loadingSymbols,
    futuresRankings,
    loadingFutures,
  };
}
