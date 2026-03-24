import { roundDecimals } from "./math";

export interface DashboardTicker {
  symbol: string;
  priceChangePercent: string;
  pricePercentageChange?: string;
  priceChgPct?: string;
}

export const normalizePriceChangePercent = (
  ticker: Partial<DashboardTicker>,
): string => {
  if (typeof ticker.priceChangePercent === "string") {
    return roundDecimals(parseFloat(ticker.priceChangePercent), 2).toString();
  }

  if (typeof ticker.pricePercentageChange === "string") {
    return roundDecimals(
      parseFloat(ticker.pricePercentageChange),
      2,
    ).toString();
  }

  if (typeof ticker.priceChgPct === "string") {
    return roundDecimals(parseFloat(ticker.priceChgPct) * 100, 2).toString();
  }

  return "0";
};
