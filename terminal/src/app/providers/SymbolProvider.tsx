import React, { type FC, type ReactNode } from "react";
import { SymbolContext, useSymbolDataProvider } from "../hooks";
import type { MarketType } from "../../utils/enums";

interface SymbolProviderProps {
  children: ReactNode;
  marketType?: MarketType;
}

export const SymbolProvider: FC<SymbolProviderProps> = ({
  children,
  marketType,
}) => {
  const symbolData = useSymbolDataProvider(marketType);

  return (
    <SymbolContext.Provider value={symbolData}>
      {children}
    </SymbolContext.Provider>
  );
};
