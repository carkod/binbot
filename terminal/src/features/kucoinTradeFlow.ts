import { floorToMultiple, isPositiveFinite } from "../utils/math";

export const TRADE_FLOW_WINDOW_MS = 15 * 60 * 1000;
const MINUTE_MS = 60_000;

export interface AggressiveTrade {
  id: string;
  timestamp: number;
  notional: number;
  side: "buy" | "sell";
}

export interface TradeFlowBucket {
  timestamp: number;
  buy: number;
  sell: number;
}

export interface TradeFlowHistory {
  buckets: TradeFlowBucket[];
  seen: Record<string, number>;
}

export const parseKucoinExecution = (
  data: unknown,
  multiplier: number,
): AggressiveTrade => {
  const trade = data as {
    tradeId?: unknown;
    ts?: unknown;
    price?: unknown;
    size?: unknown;
    side?: unknown;
  };
  const timestamp = Number(trade?.ts) / 1_000_000;
  const price = Number(trade?.price);
  const contracts = Number(trade?.size);
  const notional = price * contracts * multiplier;
  if (
    typeof trade?.tradeId !== "string" ||
    !trade.tradeId ||
    (trade.side !== "buy" && trade.side !== "sell") ||
    ![timestamp, price, contracts, multiplier, notional].every(isPositiveFinite)
  )
    throw new Error("Invalid KuCoin execution");
  return { id: trade.tradeId, timestamp, side: trade.side, notional };
};

export const accumulateTradeFlow = (
  previous: TradeFlowHistory,
  trades: AggressiveTrade[],
  now: number,
  startedAt: number,
): TradeFlowHistory => {
  const cutoff = Math.max(startedAt, now - TRADE_FLOW_WINDOW_MS);
  const firstMinute = floorToMultiple(cutoff, MINUTE_MS);
  const currentMinute = floorToMultiple(now, MINUTE_MS);
  const buckets = new Map(
    previous.buckets
      .filter(({ timestamp }) => timestamp >= firstMinute)
      .map((bucket) => [bucket.timestamp, { ...bucket }]),
  );
  const seen = Object.fromEntries(
    Object.entries(previous.seen).filter(
      ([, timestamp]) => timestamp >= cutoff,
    ),
  );
  for (
    let timestamp = firstMinute;
    timestamp <= currentMinute;
    timestamp += MINUTE_MS
  ) {
    if (!buckets.has(timestamp))
      buckets.set(timestamp, { timestamp, buy: 0, sell: 0 });
  }
  for (const trade of trades) {
    if (
      trade.timestamp < cutoff ||
      trade.timestamp > now + 1000 ||
      Object.hasOwn(seen, trade.id)
    )
      continue;
    const minute = floorToMultiple(trade.timestamp, MINUTE_MS);
    const bucket = buckets.get(minute);
    if (!bucket) continue;
    seen[trade.id] = trade.timestamp;
    bucket[trade.side] += trade.notional;
  }
  return {
    buckets: [...buckets.values()].sort((a, b) => a.timestamp - b.timestamp),
    seen,
  };
};

export const buildTradeFlowSeries = (buckets: TradeFlowBucket[]) => {
  let cumulative = 0;
  return buckets.map((bucket) => {
    const delta = bucket.buy - bucket.sell;
    cumulative += delta;
    return { ...bucket, delta, cvd: cumulative };
  });
};
