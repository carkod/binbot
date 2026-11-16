import React from "react";
import { Provider } from "react-redux";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router";
import { vi } from "vitest";
import {
  fireEvent,
  render,
  screen as rtlScreen,
  waitFor,
} from "../../../utils/render";

import { resetBot, setBot } from "../../../features/bots/botSlice";
import { MarketType } from "../../../utils/enums";
import { store } from "../../store";
import FuturesBotDetail from "../FuturesBotDetail";

const mockUseGetSingleBotQuery = vi.hoisted(() => vi.fn());
const { singleBot } = await import("../../../features/bots/botInitialState");
// Mock singleBot to have market_type FUTURES for the relevant test(s)
vi.mock("../../../features/bots/botInitialState", async () => {
  const { MarketType } = await import("../../../utils/enums");
  const original = await import("../../../features/bots/botInitialState");
  return {
    ...original,
    singleBot: { ...original.singleBot, market_type: MarketType.FUTURES },
  };
});

vi.mock("../../../features/bots/botsApiSlice", async () => {
  const actual = await vi.importActual("../../../features/bots/botsApiSlice");
  return {
    ...actual,
    useGetSingleBotQuery: mockUseGetSingleBotQuery,
  };
});

vi.mock("../../../features/balanceApiSlice", async () => {
  const actual = await vi.importActual("../../../features/balanceApiSlice");
  return {
    ...actual,
    useGetBalanceQuery: vi.fn(() => ({
      data: {
        fiat_available: 0,
        fiat_currency: "USDT",
        estimated_total_fiat: 0,
        balances: {},
      },
      isLoading: false,
    })),
  };
});

vi.mock("../../../features/autotradeApiSlice", async () => {
  const actual = await vi.importActual("../../../features/autotradeApiSlice");
  return {
    ...actual,
    useGetSettingsQuery: vi.fn(() => ({
      data: { fiat: "USDT" },
    })),
  };
});

vi.mock("../../../features/symbolsApiSlice", async () => {
  const actual = await vi.importActual("../../../features/symbolsApiSlice");
  return {
    ...actual,
    useGetSymbolsQuery: vi.fn(() => ({
      data: [{ id: "BTCUSDT" }, { id: "ETHUSDT" }],
      isFetching: false,
    })),
  };
});

// Lightweight mocks for heavy child components
vi.mock("../../components/BotChartTabs", () => {
  const ChartContainer = ({ activeTab, onTabChange }: any) => (
    <div data-testid="chart-container" data-active-tab={activeTab}>
      <button onClick={() => onTabChange("analysis")}>Select analysis</button>
      <button onClick={() => onTabChange("chart")}>Select chart</button>
    </div>
  );
  ChartContainer.displayName = "ChartContainer";
  return { default: ChartContainer };
});
vi.mock("../../components/BotInfo", () => {
  const BotInfo = ({ activeTab, onTabChange }: any) => (
    <div data-testid="bot-info" data-active-tab={activeTab}>
      <button onClick={() => onTabChange("deal")}>Select deal</button>
    </div>
  );
  BotInfo.displayName = "BotInfo";
  return { default: BotInfo };
});
vi.mock("../../components/LogsInfo", () => {
  const LogsInfo = (_props: any) => <div data-testid="logs-info" />;
  LogsInfo.displayName = "LogsInfo";
  return { default: LogsInfo };
});
vi.mock("../../components/BotDetailTabs", () => {
  const BotDetailTabs = ({ activeTab, onTabChange }: any) => (
    <div data-testid="bot-detail-tabs" data-active-tab={activeTab}>
      <button onClick={() => onTabChange("stop-loss")}>Select stop loss</button>
      <button onClick={() => onTabChange("take-profit")}>
        Select take profit
      </button>
    </div>
  );
  BotDetailTabs.displayName = "BotDetailTabs";
  return { default: BotDetailTabs };
});
vi.mock("../../components/BalanceAnalysis", () => {
  const BalanceAnalysis = (_props: any) => (
    <div data-testid="balance-analysis" />
  );
  BalanceAnalysis.displayName = "BalanceAnalysis";
  return { default: BalanceAnalysis };
});

// Local SpinnerContext fallback matching Layout signature
const SpinnerContext = React.createContext({
  spinner: false,
  setSpinner: (_value: boolean) => {},
});

const NavigateToNew = () => {
  const navigate = useNavigate();

  return (
    <button type="button" onClick={() => navigate("/bots/futures/new")}>
      New futures bot
    </button>
  );
};

const CurrentLocation = () => {
  const location = useLocation();
  return (
    <output data-testid="location">
      {location.pathname + location.search}
    </output>
  );
};

const renderDetailAt = (url: string) =>
  render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[url]}>
        <CurrentLocation />
        <Routes>
          <Route path="/bots/futures/edit/:id" element={<FuturesBotDetail />} />
        </Routes>
      </MemoryRouter>
    </Provider>,
  );

describe("FuturesBotDetail page", () => {
  beforeEach(() => {
    store.dispatch(resetBot({ market_type: MarketType.FUTURES }));
    mockUseGetSingleBotQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
    });
  });

  it("restores every selected tab after reloading the current URL", () => {
    const view = renderDetailAt("/bots/futures/edit/123?source=bots");
    fireEvent.click(rtlScreen.getByText("Select analysis"));
    fireEvent.click(rtlScreen.getByText("Select take profit"));
    fireEvent.click(rtlScreen.getByText("Select deal"));

    const url = rtlScreen.getByTestId("location").textContent!;
    expect(new URL(url, "http://localhost").searchParams.get("source")).toBe(
      "bots",
    );
    view.unmount();
    renderDetailAt(url);

    expect(
      rtlScreen.getByTestId("chart-container").getAttribute("data-active-tab"),
    ).toBe("analysis");
    expect(
      rtlScreen.getByTestId("bot-detail-tabs").getAttribute("data-active-tab"),
    ).toBe("take-profit");
    expect(
      rtlScreen.getByTestId("bot-info").getAttribute("data-active-tab"),
    ).toBe("deal");
  });

  it("updates one tab group while preserving the other selections", () => {
    renderDetailAt(
      "/bots/futures/edit/123?chartTab=analysis&settingsTab=take-profit&infoTab=deal",
    );
    fireEvent.click(rtlScreen.getByText("Select stop loss"));
    fireEvent.click(rtlScreen.getByText("Select chart"));

    const url = new URL(
      rtlScreen.getByTestId("location").textContent!,
      "http://localhost",
    );
    expect(url.searchParams.get("chartTab")).toBeNull();
    expect(url.searchParams.get("settingsTab")).toBe("stop-loss");
    expect(url.searchParams.get("infoTab")).toBe("deal");
  });

  it("uses the default tabs when the URL contains unknown selections", () => {
    renderDetailAt(
      "/bots/futures/edit/123?chartTab=unknown&settingsTab=unknown&infoTab=unknown",
    );

    expect(
      rtlScreen.getByTestId("chart-container").getAttribute("data-active-tab"),
    ).toBe("chart");
    expect(
      rtlScreen.getByTestId("bot-detail-tabs").getAttribute("data-active-tab"),
    ).toBe("main");
    expect(
      rtlScreen.getByTestId("bot-info").getAttribute("data-active-tab"),
    ).toBe("orders");
  });

  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/futures/new"]}>
            <Routes>
              <Route path="/bots/futures/new" element={<FuturesBotDetail />} />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );

    expect(container.querySelector(".content")).not.toBeNull();
    expect(rtlScreen.getByTestId("chart-container")).toBeTruthy();
  });

  it("keeps existing bot data but overrides market_type to FUTURES when editing", () => {
    render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/futures/edit/123"]}>
            <Routes>
              <Route
                path="/bots/futures/edit/:id"
                element={<FuturesBotDetail />}
              />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );

    const state = store.getState().bot.bot;
    // Existing bot is replaced with a FUTURES bot for this page
    expect(state.market_type).toBe(MarketType.FUTURES);
  });

  it("forces market_type to FUTURES when creating a new bot", () => {
    const existingBot = {
      ...singleBot,
      id: "123",
      name: "Existing spot bot",
      pair: "RAVEUSDTM",
      market_type: MarketType.SPOT,
    };

    store.dispatch(
      setBot({
        bot: existingBot,
      }),
    );

    render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/futures/new"]}>
            <Routes>
              <Route path="/bots/futures/new" element={<FuturesBotDetail />} />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );

    const state = store.getState().bot.bot;
    expect(state.id).toBe("");
    expect(state.name).toBe("terminal");
    expect(state.pair).toBe("");
    expect(state.market_type).toBe(MarketType.FUTURES);
  });

  it("uses the route symbol when creating a new futures bot from a symbol URL", () => {
    render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/futures/new/KOMAUSDTM"]}>
            <Routes>
              <Route
                path="/bots/futures/new/:symbol"
                element={<FuturesBotDetail />}
              />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );

    const state = store.getState().bot.bot;
    expect(state.pair).toBe("KOMAUSDTM");
    expect(state.market_type).toBe(MarketType.FUTURES);
  });

  it("resets stale edit details after navigating from edit to new", async () => {
    const editResponse = {
      data: {
        bot: {
          ...singleBot,
          id: "123",
          name: "RAVE futures bot",
          pair: "RAVEUSDTM",
          market_type: MarketType.FUTURES,
        },
      },
      isLoading: false,
    };
    const newResponse = {
      data: undefined,
      isLoading: false,
    };

    mockUseGetSingleBotQuery.mockImplementation((id?: string) => ({
      ...(id ? editResponse : newResponse),
    }));

    render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/futures/edit/123"]}>
            <NavigateToNew />
            <Routes>
              <Route
                path="/bots/futures/edit/:id"
                element={<FuturesBotDetail />}
              />
              <Route path="/bots/futures/new" element={<FuturesBotDetail />} />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );

    await waitFor(() => {
      expect(store.getState().bot.bot.pair).toBe("RAVEUSDTM");
    });

    fireEvent.click(rtlScreen.getByRole("button", { name: "New futures bot" }));

    await waitFor(() => {
      const state = store.getState().bot.bot;

      expect(state.id).toBe("");
      expect(state.name).toBe("terminal");
      expect(state.pair).toBe("");
      expect(state.market_type).toBe(MarketType.FUTURES);
    });
  });
});
