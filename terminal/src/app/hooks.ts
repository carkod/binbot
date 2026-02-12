// This file serves as a central hub for re-exporting pre-typed Redux hooks.
// These imports are restricted elsewhere to ensure consistent
// usage of typed hooks throughout the application.
// We disable the ESLint rule here because this is the designated place
// for importing and re-exporting the typed versions of hooks.
/* eslint-disable @typescript-eslint/no-restricted-imports */
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "./store";
import { useState, useEffect, useCallback, useContext } from "react";
import {
  useLazyGetOneSymbolQuery,
  useGetSymbolsQuery,
} from "../features/symbolsApiSlice";
import { MarketType } from "../utils/enums";
import { createContext } from "react";

// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();

export type Breakpoint = "xs" | "sm" | "md" | "lg" | "xl" | "xxl";

const resolveBreakpoint = (width: number): Breakpoint => {
  if (width < 576) return "xs";
  if (width < 768) return "sm";
  if (width < 992) return "md";
  if (width < 1200) return "lg";
  if (width < 1440) return "xl";
  return "xxl";
};

export const useBreakpoint = () => {
  const [size, setSize] = useState(() => resolveBreakpoint(window.innerWidth));
  const update = useCallback(
    () => setSize(resolveBreakpoint(window.innerWidth)),
    [setSize],
  );

  useEffect(() => {
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [update]);

  return size;
};

// Symbol Context and Hook
interface SymbolContextType {
  symbolsList: string[];
  quoteAsset: string;
  baseAsset: string;
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
  const [isLoading, setIsLoading] = useState(false);

  const updateQuoteBaseState = useCallback(
    (pair: string) => {
      setIsLoading(true);
      triggerGetOneSymbol(pair)
        .unwrap()
        .then((data) => {
          setQuoteAsset(data.quote_asset);
          setBaseAsset(data.base_asset);
          setIsLoading(false);
        })
        .catch(() => {
          setIsLoading(false);
        });
    },
    [triggerGetOneSymbol],
  );

  useEffect(() => {
    if (symbols && symbolsList.length === 0) {
      const pairs = symbols.map((symbol) => symbol.id);
      setSymbolsList(pairs);
    }
  }, [symbols, symbolsList]);

  return {
    symbolsList,
    quoteAsset,
    baseAsset,
    updateQuoteBaseState,
    isLoading,
  };
};
