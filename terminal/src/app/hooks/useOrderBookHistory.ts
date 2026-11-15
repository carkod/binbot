import { useEffect, useState } from "react";
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
) => {
  const [history, setHistory] = useState<ObiSnapshot[]>([]);
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    if (!enabled || isError || !snapshot) return;
    const receivedAt = Date.now();
    setNow(receivedAt);
    setHistory((previous) => updateObiHistory(previous, snapshot, receivedAt));
  }, [snapshot, enabled, isError]);

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
  const chartPoints: OrderBookHistoryPoint[] = [];
  history.forEach((point, index) => {
    const previous = history[index - 1];
    if (
      previous &&
      point.timestamp - previous.timestamp > 2 * OBI_POLL_INTERVAL_MS
    ) {
      chartPoints.push({
        timestamp: previous.timestamp + OBI_POLL_INTERVAL_MS,
        obi: null,
        spreadRatio: null,
        bidDepth: null,
        askDepth: null,
      });
    }
    chartPoints.push(point);
  });

  return { history, chartPoints, now };
};
