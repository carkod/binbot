import { useEffect, useState } from "react";
import {
  accumulateTradeFlow,
  parseKucoinExecution,
  pruneTradeFlowHistory,
  type AggressiveTrade,
  type TradeFlowHistory,
} from "../../features/kucoinTradeFlow";
import { floorToMultiple, isPositiveFinite } from "../../utils/math";
import {
  loadTradeFlowHistory,
  saveTradeFlowHistory,
} from "../../utils/tradeFlowStorage";

interface TradeFlowState {
  history: TradeFlowHistory;
  status: "connecting" | "live" | "disconnected";
  startedAt?: number;
  restarted: boolean;
  storageError?: boolean;
}

export const useKucoinTradeFlow = (
  symbol: string,
  enabled: boolean,
  multiplier?: number,
) => {
  const [state, setState] = useState<TradeFlowState>({
    history: { buckets: [], seen: {} },
    status: "connecting",
    restarted: false,
  });

  useEffect(() => {
    if (!enabled || !isPositiveFinite(multiplier)) return;
    setState({
      history: { buckets: [], seen: {} },
      status: "connecting",
      restarted: false,
    });
    let disposed = false;
    let socket: WebSocket | undefined;
    let retry: ReturnType<typeof setTimeout>;
    let heartbeat: ReturnType<typeof setInterval>;
    let timeout: ReturnType<typeof setTimeout>;
    let flush: ReturnType<typeof setInterval>;
    let startedAt = 0;
    let hasConnected = false;
    let hydrated = false;
    let collecting = false;
    let history: TradeFlowHistory = { buckets: [], seen: {} };
    let pending: AggressiveTrade[] = [];
    const controller = new AbortController();

    const persist = () => {
      if (!hydrated) return;
      void saveTradeFlowHistory(symbol, multiplier, history).catch(() => {
        if (!disposed)
          setState((previous) => ({ ...previous, storageError: true }));
      });
    };

    const flushPending = () => {
      if (!hydrated) return;
      const trades = pending;
      pending = [];
      history = collecting
        ? accumulateTradeFlow(history, trades, Date.now(), startedAt)
        : pruneTradeFlowHistory(history, Date.now());
      if (!disposed) setState((previous) => ({ ...previous, history }));
      persist();
    };

    const reconnect = () => {
      clearInterval(heartbeat);
      clearTimeout(timeout);
      if (disposed) return;
      flushPending();
      collecting = false;
      setState((previous) => ({ ...previous, status: "disconnected" }));
      retry = setTimeout(connect, 5000);
    };

    const connect = async () => {
      if (disposed) return;
      try {
        const response = await fetch("/kucoin-futures/api/v1/bullet-public", {
          method: "POST",
          signal: controller.signal,
        });
        const session = await response.json();
        const server = session?.data?.instanceServers?.find(
          (candidate: { protocol: string }) =>
            candidate.protocol === "websocket",
        );
        if (
          !response.ok ||
          session.code !== "200000" ||
          !session.data.token ||
          !server ||
          !isPositiveFinite(server.pingInterval) ||
          !isPositiveFinite(server.pingTimeout)
        ) {
          throw new Error("KuCoin trade stream unavailable");
        }
        if (disposed) return;
        const url = new URL(server.endpoint);
        if (url.protocol !== "wss:" || !url.hostname.endsWith(".kucoin.com"))
          throw new Error("Invalid KuCoin stream endpoint");
        url.searchParams.set("token", session.data.token);
        url.searchParams.set("connectId", crypto.randomUUID());
        socket = new WebSocket(url.toString());
        timeout = setTimeout(() => socket?.close(), server.pingTimeout);
        const topic = `/contractMarket/execution:${symbol}`;

        socket.onmessage = (event) => {
          if (disposed) return;
          try {
            const message = JSON.parse(event.data);
            if (message.type === "welcome") {
              socket?.send(
                JSON.stringify({
                  id: "subscribe",
                  type: "subscribe",
                  topic,
                  privateChannel: false,
                  response: true,
                }),
              );
            } else if (message.type === "ack" && message.id === "subscribe") {
              if (collecting) return;
              clearTimeout(timeout);
              startedAt = Date.now();
              pending = [];
              history = pruneTradeFlowHistory(history, startedAt);
              const restored = history.buckets.length > 0;
              history = accumulateTradeFlow(history, [], startedAt, startedAt);
              if (restored) {
                const minute = floorToMultiple(startedAt, 60_000);
                history.buckets = history.buckets.map((bucket) =>
                  bucket.timestamp === minute
                    ? { ...bucket, gapBefore: true }
                    : bucket,
                );
              }
              collecting = true;
              const restarted = hasConnected || restored;
              setState((previous) => ({
                ...previous,
                history,
                status: "live",
                startedAt,
                restarted,
              }));
              hasConnected = true;
              persist();
              heartbeat = setInterval(() => {
                if (socket?.readyState !== WebSocket.OPEN) return;
                socket.send(JSON.stringify({ id: "heartbeat", type: "ping" }));
                timeout = setTimeout(() => socket?.close(), server.pingTimeout);
              }, server.pingInterval);
            } else if (message.type === "pong") {
              clearTimeout(timeout);
            } else if (
              collecting &&
              message.type === "message" &&
              message.topic === topic
            ) {
              pending.push(parseKucoinExecution(message.data, multiplier));
            } else if (message.type === "error") {
              socket?.close();
            }
          } catch {
            // Unknown/malformed executions make coverage uncertain.
            socket?.close();
          }
        };
        socket.onerror = () => socket?.close();
        socket.onclose = reconnect;
      } catch {
        reconnect();
      }
    };
    const initialize = async () => {
      try {
        const stored = await loadTradeFlowHistory(symbol, multiplier);
        if (disposed) return;
        history = pruneTradeFlowHistory(stored, Date.now());
        setState((previous) => ({
          ...previous,
          history,
          restarted: history.buckets.length > 0,
        }));
      } catch {
        if (disposed) return;
        setState((previous) => ({ ...previous, storageError: true }));
      }
      hydrated = true;
      flush = setInterval(flushPending, 1000);
      void connect();
    };
    window.addEventListener("pagehide", flushPending);
    void initialize();
    return () => {
      disposed = true;
      flushPending();
      collecting = false;
      window.removeEventListener("pagehide", flushPending);
      controller.abort();
      clearTimeout(retry);
      clearTimeout(timeout);
      clearInterval(heartbeat);
      clearInterval(flush);
      socket?.close();
    };
  }, [symbol, enabled, multiplier]);

  return state;
};
