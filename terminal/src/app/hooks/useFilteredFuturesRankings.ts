import { useMemo } from "react";
import { useFuturesRankingsQuery } from "../../features/kucoinApiSlice";
import { useGetSymbolsQuery } from "../../features/symbolsApiSlice";
import { normalizePriceChangePercent } from "../../utils/gainers-losers";

export function useFilteredFuturesRankings() {
  const { data: apiSymbols = [], isLoading: loadingSymbols } =
    useGetSymbolsQuery();
  const { data: futuresRankings = [], isLoading: loadingFutures } =
    useFuturesRankingsQuery();

  const combined = useMemo(() => {
    const symbolMap = new Map(apiSymbols.map((symbol) => [symbol.id, symbol]));
    return futuresRankings
      .filter((ranking) => symbolMap.has(ranking.symbol))
      .map((ranking) => ({
        ...ranking,
        priceChangePercent: normalizePriceChangePercent(ranking),
        apiSymbol: symbolMap.get(ranking.symbol),
      }));
  }, [apiSymbols, futuresRankings]);

  return {
    combined,
    isLoading: loadingSymbols || loadingFutures,
  };
}
