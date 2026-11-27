export const TRADES_WINDOW_MS = 5 * 60_000;

export const TRADES_POLL_INTERVAL_MS = 5_000;

export interface KucoinMarketTrade {
  tradeId: string;
  side: "buy" | "sell";
  price: number;
  /** Contracts, not base-asset units. */
  size: number;
  /** Milliseconds since the Unix epoch. */
  timestamp: number;
}

export interface KucoinTradesSummary {
  trades: (KucoinMarketTrade & { notional: number })[];
  buy: number;
  sell: number;
  delta: number;
}

/**
 * Keep trades from the last window and value them in USDT.
 * Notional is price x contracts x multiplier, the same formula the stored CVD uses.
 */
export const summarizeRecentTrades = (
  trades: KucoinMarketTrade[],
  multiplier: number,
  now: number,
  windowMs = TRADES_WINDOW_MS,
): KucoinTradesSummary => {
  const recent = trades
    .filter(({ timestamp }) => timestamp >= now - windowMs && timestamp <= now)
    .sort((left, right) => left.timestamp - right.timestamp)
    .map((trade) => ({
      ...trade,
      notional: trade.price * trade.size * multiplier,
    }));

  const buy = recent
    .filter(({ side }) => side === "buy")
    .reduce((total, { notional }) => total + notional, 0);

  const sell = recent
    .filter(({ side }) => side === "sell")
    .reduce((total, { notional }) => total + notional, 0);

  return { trades: recent, buy, sell, delta: buy - sell };
};
