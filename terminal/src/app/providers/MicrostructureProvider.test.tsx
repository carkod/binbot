import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router";
import { vi } from "vitest";
import { MicrostructureProvider } from "./MicrostructureProvider";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import { saveTradeFlowHistory } from "../../utils/tradeFlowStorage";

vi.mock("../../features/kucoinApiSlice", () => ({
  useFuturesLiquidityQuery: vi.fn(),
}));
vi.mock("../../utils/tradeFlowStorage", () => ({
  loadTradeFlowHistory: vi.fn(async () => ({ buckets: [], seen: {} })),
  saveTradeFlowHistory: vi.fn(async () => undefined),
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
const snapshot = {
  timestamp: now,
  liquidity: "High liquidity",
  obi: 0.2,
  spreadRatio: 0.0008,
  bidDepth: 30,
  askDepth: 20,
  multiplier: 10,
};
const queryResult = (timestamp = now) =>
  ({
    currentData: { ...snapshot, timestamp },
    isError: false,
    isFetching: false,
    refetch: vi.fn(),
  }) as ReturnType<typeof useFuturesLiquidityQuery>;

const Controls = () => {
  const navigate = useNavigate();
  return (
    <>
      <button onClick={() => navigate("/dashboard")}>Dashboard</button>
      <button onClick={() => navigate("/microstructure/KGENUSDTM")}>
        KGEN
      </button>
      <button onClick={() => navigate("/microstructure/XBTUSDTM")}>XBT</button>
    </>
  );
};
const Probe = () => {
  const { symbol, tradeFlow, orderBookHistory } = useMicrostructureData();
  return (
    <output data-testid="collector">
      {JSON.stringify({
        symbol,
        tradeFlow,
        timestamps: orderBookHistory.history.map(({ timestamp }) => timestamp),
      })}
    </output>
  );
};
const renderCollector = (path = "/microstructure/KGENUSDTM") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <MicrostructureProvider>
        <Controls />
        <Routes>
          <Route path="/microstructure/:symbol?" element={<Probe />} />
          <Route path="/dashboard" element={<p>Other page</p>} />
        </Routes>
      </MicrostructureProvider>
    </MemoryRouter>,
  );

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

const sendTrade = (socket: MockSocket, id: string, symbol = "KGENUSDTM") =>
  socket.message({
    type: "message",
    topic: `/contractMarket/execution:${symbol}`,
    data: {
      tradeId: id,
      ts: Date.now() * 1_000_000,
      price: "0.075",
      size: 20,
      side: "buy",
    },
  });

describe("background microstructure collectors", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(now);
    MockSocket.sockets = [];
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue(queryResult());
    vi.stubGlobal("WebSocket", MockSocket);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
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
      })),
    );
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("keeps the stream, order-book history and persistence running after leaving the page", async () => {
    const { unmount } = renderCollector();
    const socket = await connectSocket();
    act(() => {
      sendTrade(socket, "before");
      vi.advanceTimersByTime(1000);
    });
    fireEvent.click(testingScreen.getByRole("button", { name: "Dashboard" }));
    expect(testingScreen.queryByTestId("collector")).not.toBeInTheDocument();
    expect(socket.close).not.toHaveBeenCalled();
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue(
      queryResult(now + 15_000),
    );
    act(() => {
      sendTrade(socket, "away");
      vi.advanceTimersByTime(14_000);
    });
    expect(saveTradeFlowHistory).toHaveBeenLastCalledWith(
      "KGENUSDTM",
      10,
      expect.objectContaining({
        buckets: [expect.objectContaining({ buy: 30 })],
      }),
    );
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "KGENUSDTM",
      expect.objectContaining({
        skip: false,
        pollingInterval: 15_000,
        skipPollingIfUnfocused: false,
      }),
    );
    fireEvent.click(testingScreen.getByRole("button", { name: "KGEN" }));
    const restored = JSON.parse(
      testingScreen.getByTestId("collector").textContent,
    );
    expect(restored.tradeFlow.history.buckets[0].buy).toBe(30);
    expect(restored.tradeFlow.restarted).toBe(false);
    expect(restored.timestamps).toEqual([now, now + 15_000]);
    expect(MockSocket.sockets).toHaveLength(1);
    unmount();
    expect(socket.close).toHaveBeenCalledOnce();
  });

  it("switches to one new collector when the route symbol changes", async () => {
    renderCollector();
    const first = await connectSocket();
    act(() => sendTrade(first, "pending"));
    fireEvent.click(testingScreen.getByRole("button", { name: "XBT" }));
    expect(first.close).toHaveBeenCalledOnce();
    expect(saveTradeFlowHistory).toHaveBeenCalledWith(
      "KGENUSDTM",
      10,
      expect.objectContaining({
        buckets: [expect.objectContaining({ buy: 15 })],
      }),
    );
    const second = await connectSocket();
    expect(second.send).toHaveBeenCalledWith(
      expect.stringContaining("/contractMarket/execution:XBTUSDTM"),
    );
    expect(MockSocket.sockets).toHaveLength(2);
    act(() => {
      sendTrade(first, "late");
      sendTrade(second, "new", "XBTUSDTM");
      vi.advanceTimersByTime(1000);
    });
    const current = JSON.parse(
      testingScreen.getByTestId("collector").textContent,
    );
    expect(current.symbol).toBe("XBTUSDTM");
    expect(current.tradeFlow.history.buckets[0].buy).toBe(15);
    expect(current.tradeFlow.history.seen.pending).toBeUndefined();
  });

  it("does not start collecting before the user selects a symbol", () => {
    renderCollector("/dashboard");
    expect(MockSocket.sockets).toHaveLength(0);
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "",
      expect.objectContaining({ skip: true }),
    );
  });

  it("keeps a validated trade stream alive during an order-book refresh failure", async () => {
    renderCollector();
    const socket = await connectSocket();
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue({
      ...queryResult(),
      isError: true,
    } as ReturnType<typeof useFuturesLiquidityQuery>);
    act(() => vi.advanceTimersByTime(1000));
    expect(socket.close).not.toHaveBeenCalled();
    expect(MockSocket.sockets).toHaveLength(1);
  });
});
