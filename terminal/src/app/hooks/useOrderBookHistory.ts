import { useEffect, useMemo, useState } from "react";
import {
  OBI_POLL_INTERVAL_MS,
  updateObiHistory,
  type ObiSnapshot,
} from "../../features/kucoinLiquidity";

interface OrderBookHistoryPoint {
  timestamp: number;
  obi: number | null;
  spreadRatio: number | null;
  bidDepth: number | null;
  askDepth: number | null;
}

export const useOrderBookHistory = (
  snapshot: ObiSnapshot | undefined,
  enabled: boolean,
  isError: boolean,
  symbol = "",
) => {
  const [history, setHistory] = useState<ObiSnapshot[]>([]);
  const [now, setNow] = useState(Date.now);
  const [historySymbol, setHistorySymbol] = useState(symbol);

  if (historySymbol !== symbol) {
    setHistorySymbol(symbol);
    setHistory([]);
    setNow(Date.now());
  }

  useEffect(() => {
    if (!enabled || isError || !snapshot) return;
    const receivedAt = Date.now();
    setNow(receivedAt);
    setHistory((previous) => updateObiHistory(previous, snapshot, receivedAt));
  }, [snapshot, enabled, isError, symbol]);

  useEffect(() => {
    const interval = setInterval(() => {
      const currentTime = Date.now();
      setNow(currentTime);
      setHistory((previous) =>
        updateObiHistory(previous, undefined, currentTime),
      );
    }, OBI_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  // Break lines across missed polls instead of implying measurements in gaps.
  const chartPoints = useMemo(() => {
    const points: OrderBookHistoryPoint[] = [];
    history.forEach((point, index) => {
      const previous = history[index - 1];
      if (
        previous &&
        point.timestamp - previous.timestamp > 2 * OBI_POLL_INTERVAL_MS
      ) {
        points.push({
          timestamp: previous.timestamp + OBI_POLL_INTERVAL_MS,
          obi: null,
          spreadRatio: null,
          bidDepth: null,
          askDepth: null,
        });
      }
      points.push(point);
    });
    return points;
  }, [history]);

  return { history, chartPoints, now };
};
