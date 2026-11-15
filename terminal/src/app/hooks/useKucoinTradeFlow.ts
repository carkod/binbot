import { useEffect, useState } from "react";
import {
  accumulateTradeFlow,
  parseKucoinExecution,
  type AggressiveTrade,
  type TradeFlowHistory,
} from "../../features/kucoinTradeFlow";

interface TradeFlowState {
  history: TradeFlowHistory;
  status: "connecting" | "live" | "disconnected";
  startedAt?: number;
  restarted: boolean;
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
    if (!enabled || !multiplier || !Number.isFinite(multiplier)) return;
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
    let pending: AggressiveTrade[] = [];
    const controller = new AbortController();

    const reconnect = () => {
      clearInterval(heartbeat);
      clearInterval(flush);
      clearTimeout(timeout);
      if (disposed) return;
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
          !Number.isFinite(server.pingInterval) ||
          server.pingInterval <= 0 ||
          !Number.isFinite(server.pingTimeout) ||
          server.pingTimeout <= 0
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
              clearTimeout(timeout);
              startedAt = Date.now();
              pending = [];
              setState({
                history: accumulateTradeFlow(
                  { buckets: [], seen: {} },
                  [],
                  startedAt,
                  startedAt,
                ),
                status: "live",
                startedAt,
                restarted: hasConnected,
              });
              hasConnected = true;
              flush = setInterval(() => {
                const trades = pending;
                pending = [];
                setState((previous) => ({
                  ...previous,
                  history: accumulateTradeFlow(
                    previous.history,
                    trades,
                    Date.now(),
                    startedAt,
                  ),
                }));
              }, 1000);
              heartbeat = setInterval(() => {
                if (socket?.readyState !== WebSocket.OPEN) return;
                socket.send(JSON.stringify({ id: "heartbeat", type: "ping" }));
                timeout = setTimeout(() => socket?.close(), server.pingTimeout);
              }, server.pingInterval);
            } else if (message.type === "pong") {
              clearTimeout(timeout);
            } else if (message.type === "message" && message.topic === topic) {
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
    void connect();
    return () => {
      disposed = true;
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
