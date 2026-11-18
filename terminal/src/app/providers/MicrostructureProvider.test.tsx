import "@testing-library/jest-dom";
import { useEffect } from "react";
import {
  MemoryRouter,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router";
import { vi } from "vitest";
import { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
} from "../../utils/render";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import { MicrostructureProvider } from "./MicrostructureProvider";

vi.mock("../../features/kucoinApiSlice", () => ({
  useFuturesLiquidityQuery: vi.fn(),
}));

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

  const { selectSymbol } = useMicrostructureData();

  return (
    <>
      <input aria-label="Bot form state" defaultValue="draft" />
      <button onClick={() => navigate("/dashboard")}>Dashboard</button>
      <button onClick={() => navigate("/bots/futures/new/KGENUSDTM")}>
        KGEN
      </button>
      <button onClick={() => navigate("/bots/futures/new/XBTUSDTM")}>
        XBT
      </button>
      <button onClick={() => selectSymbol("KGENUSDTM")}>Bot KGEN</button>
      <button onClick={() => selectSymbol("XBTUSDTM")}>Bot XBT</button>
    </>
  );
};

const Probe = () => {
  const { symbol: botSymbol } = useParams();

  const { symbol, selectSymbol, orderBookHistory } = useMicrostructureData();

  useEffect(() => {
    if (botSymbol) selectSymbol(botSymbol);
  }, [botSymbol, selectSymbol]);
  return (
    <output data-testid="collector">
      {JSON.stringify({
        symbol,
        timestamps: orderBookHistory.history.map(({ timestamp }) => timestamp),
      })}
    </output>
  );
};

const renderCollector = (path = "/bots/futures/new/KGENUSDTM") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <MicrostructureProvider>
        <Controls />
        <Routes>
          <Route path="/bots/futures/new/:symbol" element={<Probe />} />
          <Route path="/dashboard" element={<p>Other page</p>} />
        </Routes>
      </MicrostructureProvider>
    </MemoryRouter>,
  );

describe("background order-book collection", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(now);
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue(queryResult());
  });
  afterEach(() => vi.useRealTimers());

  it("keeps order-book history across navigation and polls while unfocused", () => {
    renderCollector();
    fireEvent.click(testingScreen.getByRole("button", { name: "Dashboard" }));
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue(
      queryResult(now + 15_000),
    );
    act(() => vi.advanceTimersByTime(15_000));
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

    expect(restored.timestamps).toEqual([now, now + 15_000]);
  });

  it("resets order-book history when the route symbol changes", () => {
    renderCollector();
    vi.mocked(useFuturesLiquidityQuery).mockReturnValue(
      queryResult(now + 15_000),
    );
    act(() => vi.advanceTimersByTime(15_000));

    const previousSymbol = queryResult(now + 15_000);

    const nextSymbol = queryResult(now + 30_000);

    vi.mocked(useFuturesLiquidityQuery).mockImplementation((symbol) =>
      symbol === "XBTUSDTM" ? nextSymbol : previousSymbol,
    );
    fireEvent.click(testingScreen.getByRole("button", { name: "XBT" }));
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "XBTUSDTM",
      expect.objectContaining({ skip: false }),
    );

    const current = JSON.parse(
      testingScreen.getByTestId("collector").textContent,
    );

    expect(current.symbol).toBe("XBTUSDTM");
    expect(current.timestamps).toEqual([now + 30_000]);
  });

  it("waits for symbol selection and preserves bot form state while switching", () => {
    renderCollector("/dashboard");
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "",
      expect.objectContaining({ skip: true }),
    );

    const form = testingScreen.getByRole("textbox", { name: "Bot form state" });

    fireEvent.change(form, { target: { value: "edited draft" } });
    fireEvent.click(testingScreen.getByRole("button", { name: "Bot KGEN" }));
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "KGENUSDTM",
      expect.objectContaining({ skip: false }),
    );
    fireEvent.click(testingScreen.getByRole("button", { name: "Bot XBT" }));
    expect(useFuturesLiquidityQuery).toHaveBeenLastCalledWith(
      "XBTUSDTM",
      expect.objectContaining({ skip: false }),
    );
    expect(testingScreen.getByRole("textbox", { name: "Bot form state" })).toBe(
      form,
    );
    expect(form).toHaveValue("edited draft");
  });
});
