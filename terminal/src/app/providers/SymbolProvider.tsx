import React, { type FC, type ReactNode } from "react";
import { SymbolContext, useSymbolDataProvider } from "../hooks";

interface SymbolProviderProps {
  children: ReactNode;
}

export const SymbolProvider: FC<SymbolProviderProps> = ({ children }) => {
  const symbolData = useSymbolDataProvider();

  return (
    <SymbolContext.Provider value={symbolData}>
      {children}
    </SymbolContext.Provider>
  );
};
