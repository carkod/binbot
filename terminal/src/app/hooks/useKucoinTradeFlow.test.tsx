import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";
import { useKucoinTradeFlow } from "./useKucoinTradeFlow";

class MockSocket {
  static OPEN = 1;
  static sockets: MockSocket[] = [];
  readyState = 1;
  onmessage?: (event: { data: string }) => void;
  onclose?: () => void;
  onerror?: () => void;
  send = vi.fn();
  constructor(public url: string) {
    MockSocket.sockets.push(this);
  }
  close = vi.fn(() => {
    this.readyState = 3;
    this.onclose?.();
  });
  message(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

const now = 1_790_000_040_000;
const fetchMock = vi.fn();

const connectSocket = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
  const socket = MockSocket.sockets.at(-1);
  act(() => {
    socket.message({ type: "welcome" });
    socket.message({ type: "ack", id: "subscribe" });
  });
  return socket;
};

describe("terminal trade stream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(now);
    MockSocket.sockets = [];
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        code: "200000",
        data: {
          token: "public-token",
          instanceServers: [
            {
              protocol: "websocket",
              endpoint: "wss://ws-api-futures.kucoin.com/",
              pingInterval: 18_000,
              pingTimeout: 10_000,
            },
          ],
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("WebSocket", MockSocket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("subscribes to the selected symbol, batches trades, and cleans up on unmount", async () => {
    const { result, unmount } = renderHook(() =>
      useKucoinTradeFlow("KGENUSDTM", true, 10),
    );
    const socket = await connectSocket();
    expect(socket.send).toHaveBeenCalledWith(
      expect.stringContaining("/contractMarket/execution:KGENUSDTM"),
    );
    expect(result.current.status).toBe("live");
    const message = {
      type: "message",
      topic: "/contractMarket/execution:KGENUSDTM",
      data: {
        tradeId: "trade",
        ts: now * 1_000_000,
        size: 20,
        price: "0.075",
        side: "buy",
      },
    };
    act(() => {
      socket.message(message);
      socket.message(message);
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.history.buckets[0].buy).toBe(15);
    unmount();
    expect(socket.close).toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(60_000));
    expect(MockSocket.sockets).toHaveLength(1);
  });

  it("marks disconnection and starts a fresh accumulation after reconnect", async () => {
    const { result } = renderHook(() =>
      useKucoinTradeFlow("KGENUSDTM", true, 10),
    );
    const socket = await connectSocket();
    act(() => socket.close());
    expect(result.current.status).toBe("disconnected");
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    await connectSocket();
    expect(result.current.status).toBe("live");
    expect(result.current.restarted).toBe(true);
    expect(result.current.history.buckets[0]).toMatchObject({
      buy: 0,
      sell: 0,
    });
  });

  it("closes a stalled connection when a heartbeat is not acknowledged", async () => {
    const { result } = renderHook(() =>
      useKucoinTradeFlow("KGENUSDTM", true, 10),
    );
    const socket = await connectSocket();
    act(() => vi.advanceTimersByTime(18_000));
    expect(socket.send).toHaveBeenCalledWith(
      expect.stringContaining('"type":"ping"'),
    );
    act(() => vi.advanceTimersByTime(10_000));
    expect(socket.close).toHaveBeenCalled();
    expect(result.current.status).toBe("disconnected");
  });

  it("does not connect before a symbol and valid contract multiplier are available", () => {
    renderHook(() => useKucoinTradeFlow("", false));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
