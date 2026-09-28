import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  useGetSymbolsQuery,
  useLazyGetOneSymbolQuery,
} from "../../features/symbolsApiSlice";
import type { MarketType } from "../../utils/enums";

interface SymbolContextType {
  symbolsList: string[];
  quoteAsset: string;
  baseAsset: string;
  futuresLeverage: number;
  updateQuoteBaseState: (pair: string) => void;
  isLoading: boolean;
}

export const SymbolContext = createContext<SymbolContextType | undefined>(
  undefined,
);

export const useSymbolData = () => {
  const context = useContext(SymbolContext);
  if (!context) {
    throw new Error("useSymbolData must be used within a SymbolProvider");
  }
  return context;
};

export const useSymbolDataProvider = (marketType?: MarketType) => {
  const { data: symbols } = useGetSymbolsQuery(
    marketType ? { market_type: marketType } : undefined,
  );
  const [triggerGetOneSymbol] = useLazyGetOneSymbolQuery();
  const [symbolsList, setSymbolsList] = useState<string[]>([]);
  const [quoteAsset, setQuoteAsset] = useState<string>("");
  const [baseAsset, setBaseAsset] = useState<string>("");
  const [futuresLeverage, setFuturesLeverage] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(false);
  const latestSymbolRequestRef = useRef<string | null>(null);

  const updateQuoteBaseState = useCallback(
    (pair: string) => {
      latestSymbolRequestRef.current = pair;
      setIsLoading(true);
      triggerGetOneSymbol(pair)
        .unwrap()
        .then((data) => {
          if (latestSymbolRequestRef.current !== pair) {
            return;
          }

          setQuoteAsset(data.quote_asset);
          setBaseAsset(data.base_asset);
          setFuturesLeverage(data.futures_leverage);
          setIsLoading(false);
        })
        .catch(() => {
          if (latestSymbolRequestRef.current !== pair) {
            return;
          }

          setIsLoading(false);
        });
    },
    [triggerGetOneSymbol],
  );

  useEffect(() => {
    if (!symbols) {
      return;
    }

    const pairs = symbols.map((symbol) => symbol.id);

    setSymbolsList((prev) => {
      if (prev.length === pairs.length) {
        const hasSameValues = prev.every((id, index) => id === pairs[index]);
        if (hasSameValues) {
          return prev;
        }
      }

      return pairs;
    });
  }, [symbols]);

  return {
    symbolsList,
    quoteAsset,
    baseAsset,
    futuresLeverage,
    updateQuoteBaseState,
    isLoading,
  };
};
