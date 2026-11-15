import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";
import { useKucoinTradeFlow } from "./useKucoinTradeFlow";
import {
  loadTradeFlowHistory,
  saveTradeFlowHistory,
} from "../../utils/tradeFlowStorage";

vi.mock("../../utils/tradeFlowStorage", () => ({
  loadTradeFlowHistory: vi.fn(),
  saveTradeFlowHistory: vi.fn(),
}));

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
    vi.mocked(loadTradeFlowHistory).mockResolvedValue({
      buckets: [],
      seen: {},
    });
    vi.mocked(saveTradeFlowHistory).mockResolvedValue();
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
    expect(result.current.restarted).toBe(false);
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

  it("marks disconnection and retains observations after reconnect", async () => {
    const { result } = renderHook(() =>
      useKucoinTradeFlow("KGENUSDTM", true, 10),
    );
    const socket = await connectSocket();
    act(() =>
      socket.message({
        type: "message",
        topic: "/contractMarket/execution:KGENUSDTM",
        data: {
          tradeId: "before-close",
          ts: now * 1_000_000,
          size: 20,
          price: "0.075",
          side: "buy",
        },
      }),
    );
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
      buy: 15,
      sell: 0,
    });
  });

  it("restores saved data and keeps deduplication IDs when resuming collection", async () => {
    const previous = {
      buckets: [{ timestamp: now - 60_000, buy: 15, sell: 0 }],
      seen: { previous: now - 60_000 },
    };
    vi.mocked(loadTradeFlowHistory).mockResolvedValueOnce(previous);
    const { result } = renderHook(() =>
      useKucoinTradeFlow("KGENUSDTM", true, 10),
    );
    const socket = await connectSocket();
    expect(loadTradeFlowHistory).toHaveBeenCalledWith("KGENUSDTM", 10);
    expect(result.current.history.buckets[0].buy).toBe(15);
    expect(result.current.history.seen.previous).toBe(now - 60_000);
    expect(result.current.restarted).toBe(true);
    act(() => {
      const trade = {
        type: "message",
        topic: "/contractMarket/execution:KGENUSDTM",
        data: {
          tradeId: "new",
          ts: now * 1_000_000,
          size: 20,
          price: "0.075",
          side: "buy",
        },
      };
      socket.message(trade);
      socket.message(trade);
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.history.buckets.map(({ buy }) => buy)).toEqual([
      15, 15,
    ]);
    expect(result.current.history.buckets[1].gapBefore).toBe(true);
  });

  it("saves pending executions when navigating away and restores them on return", async () => {
    let saved = { buckets: [], seen: {} } as Awaited<
      ReturnType<typeof loadTradeFlowHistory>
    >;
    vi.mocked(saveTradeFlowHistory).mockImplementation(
      async (_symbol, _multiplier, history) => {
        saved = structuredClone(history);
      },
    );
    vi.mocked(loadTradeFlowHistory).mockImplementation(async () => saved);
    const first = renderHook(() => useKucoinTradeFlow("KGENUSDTM", true, 10));
    const socket = await connectSocket();
    act(() =>
      socket.message({
        type: "message",
        topic: "/contractMarket/execution:KGENUSDTM",
        data: {
          tradeId: "pending",
          ts: now * 1_000_000,
          size: 20,
          price: "0.075",
          side: "buy",
        },
      }),
    );
    first.unmount();
    expect(saved.buckets[0].buy).toBe(15);
    const second = renderHook(() => useKucoinTradeFlow("KGENUSDTM", true, 10));
    await connectSocket();
    expect(second.result.current.history.buckets[0].buy).toBe(15);
  });

  it("keeps live collection working when browser storage is unavailable", async () => {
    vi.mocked(loadTradeFlowHistory).mockRejectedValueOnce(
      new Error("Storage unavailable"),
    );
    vi.mocked(saveTradeFlowHistory).mockRejectedValue(
      new Error("Storage unavailable"),
    );
    const { result } = renderHook(() =>
      useKucoinTradeFlow("KGENUSDTM", true, 10),
    );
    await connectSocket();
    expect(result.current.status).toBe("live");
    expect(result.current.storageError).toBe(true);
  });

  it("ignores a late restore from the previous symbol", async () => {
    let resolvePrevious: (
      value: Awaited<ReturnType<typeof loadTradeFlowHistory>>,
    ) => void;
    vi.mocked(loadTradeFlowHistory).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePrevious = resolve;
        }),
    );
    const { result, rerender } = renderHook(
      ({ symbol }) => useKucoinTradeFlow(symbol, true, 10),
      { initialProps: { symbol: "KGENUSDTM" } },
    );
    rerender({ symbol: "XBTUSDTM" });
    const socket = await connectSocket();
    await act(async () =>
      resolvePrevious({
        buckets: [{ timestamp: now, buy: 100, sell: 0 }],
        seen: {},
      }),
    );
    expect(socket.send).toHaveBeenCalledWith(
      expect.stringContaining("/contractMarket/execution:XBTUSDTM"),
    );
    expect(result.current.history.buckets[0].buy).toBe(0);
    expect(MockSocket.sockets).toHaveLength(1);
    expect(saveTradeFlowHistory).not.toHaveBeenCalledWith(
      "KGENUSDTM",
      expect.anything(),
      expect.anything(),
    );
  });

  it("flushes pending executions when the browser hides the page", async () => {
    renderHook(() => useKucoinTradeFlow("KGENUSDTM", true, 10));
    const socket = await connectSocket();
    act(() => {
      socket.message({
        type: "message",
        topic: "/contractMarket/execution:KGENUSDTM",
        data: {
          tradeId: "pending",
          ts: now * 1_000_000,
          size: 20,
          price: "0.075",
          side: "buy",
        },
      });
      window.dispatchEvent(new Event("pagehide"));
    });
    expect(saveTradeFlowHistory).toHaveBeenLastCalledWith(
      "KGENUSDTM",
      10,
      expect.objectContaining({
        buckets: [expect.objectContaining({ buy: 15 })],
      }),
    );
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
