import { isPositiveFinite } from "../utils/math";

export type LiquidityLabel = "High liquidity" | "Low liquidity";

export interface KucoinMicrostructure {
  liquidity: LiquidityLabel;
  obi: number | null;
  spreadRatio: number;
  bidDepth: number;
  askDepth: number;
}

export interface ObiSnapshot extends KucoinMicrostructure {
  timestamp: number;
  multiplier: number;
}

export interface KucoinOrderBook {
  symbol: string;
  ts: number | string;
  bids: [number | string, number | string][];
  asks: [number | string, number | string][];
}

// Initial heuristic for linear USDT futures: a spread no wider than 0.1%,
// with at least 10,000 USDT on EACH side within 0.5% of the midpoint.
// Visible depth is a snapshot, not a prediction of direction or future fills.
const MAX_SPREAD_RATIO = 0.001;

const DEPTH_BAND_RATIO = 0.005;

const MIN_SIDE_NOTIONAL_USDT = 10_000;

export const OBI_WINDOW_MS = 15 * 60 * 1000;

export const OBI_POLL_INTERVAL_MS = 15_000;

export const analyzeKucoinOrderBook = (
  book: KucoinOrderBook,
  multiplier: number,
): KucoinMicrostructure => {
  if (
    !isPositiveFinite(multiplier) ||
    !Array.isArray(book?.bids) ||
    !Array.isArray(book?.asks) ||
    book.bids.length === 0 ||
    book.asks.length === 0
  ) {
    throw new Error("Incomplete KuCoin liquidity data");
  }

  const [bids, asks] = [book.bids, book.asks].map((levels) =>
    levels.map((level) => {
      if (!Array.isArray(level) || level.length < 2) {
        throw new Error("Invalid KuCoin order-book level");
      }

      const price = Number(level[0]);

      const contracts = Number(level[1]);

      if (![price, contracts].every(isPositiveFinite)) {
        throw new Error("Invalid KuCoin order-book level");
      }
      return { price, notional: price * contracts * multiplier };
    }),
  );

  const bestBid = Math.max(...bids.map(({ price }) => price));

  const bestAsk = Math.min(...asks.map(({ price }) => price));

  if (bestAsk <= bestBid) {
    throw new Error("Crossed KuCoin order book");
  }

  const midpoint = (bestBid + bestAsk) / 2;

  const spreadRatio = (bestAsk - bestBid) / midpoint;

  const bidDepth = bids
    .filter(({ price }) => price >= midpoint * (1 - DEPTH_BAND_RATIO))
    .reduce((total, { notional }) => total + notional, 0);

  const askDepth = asks
    .filter(({ price }) => price <= midpoint * (1 + DEPTH_BAND_RATIO))
    .reduce((total, { notional }) => total + notional, 0);

  const totalDepth = bidDepth + askDepth;

  return {
    liquidity:
      spreadRatio <= MAX_SPREAD_RATIO &&
      Math.min(bidDepth, askDepth) >= MIN_SIDE_NOTIONAL_USDT
        ? "High liquidity"
        : "Low liquidity",
    obi: totalDepth > 0 ? (bidDepth - askDepth) / totalDepth : null,
    spreadRatio,
    bidDepth,
    askDepth,
  };
};

export const updateObiHistory = (
  history: ObiSnapshot[],
  snapshot: ObiSnapshot | undefined,
  now: number,
): ObiSnapshot[] => {
  const cutoff = now - OBI_WINDOW_MS;

  const retained = history.filter(({ timestamp }) => timestamp >= cutoff);

  if (
    !snapshot ||
    snapshot.timestamp < cutoff ||
    !Number.isFinite(snapshot.timestamp)
  ) {
    return retained;
  }
  // Polling may return the same exchange snapshot more than once.
  if (retained.some(({ timestamp }) => timestamp === snapshot.timestamp)) {
    return retained;
  }
  return [...retained, snapshot].sort((a, b) => a.timestamp - b.timestamp);
};
