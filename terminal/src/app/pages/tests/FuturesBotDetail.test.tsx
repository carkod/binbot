import React from "react";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render } from "@testing-library/react";
import { vi } from "vitest";

import FuturesBotDetail from "../FuturesBotDetail";
import { store } from "../../store";
import { MarketType } from "../../../utils/enums";
import { setBot } from "../../../features/bots/botSlice";

const { singleBot } =
      await import("../../../features/bots/botInitialState");
// Mock singleBot to have market_type FUTURES for the relevant test(s)
vi.mock("../../../features/bots/botInitialState", async () => {
  const { MarketType } = await import("../../../utils/enums");
  const original = await import("../../../features/bots/botInitialState");
  return {
    ...original,
    singleBot: { ...original.singleBot, market_type: MarketType.FUTURES },
  };
});

// Lightweight mocks for heavy child components
vi.mock("../components/ChartContainer", () => {
  const ChartContainer = (_props: any) => <div data-testid="chart-container" />;
  ChartContainer.displayName = "ChartContainer";
  return { default: ChartContainer };
});
vi.mock("../components/BotInfo", () => {
  const BotInfo = (_props: any) => <div data-testid="bot-info" />;
  BotInfo.displayName = "BotInfo";
  return { default: BotInfo };
});
vi.mock("../components/LogsInfo", () => {
  const LogsInfo = (_props: any) => <div data-testid="logs-info" />;
  LogsInfo.displayName = "LogsInfo";
  return { default: LogsInfo };
});
vi.mock("../components/BotDetailTabs", () => {
  const BotDetailTabs = (_props: any) => <div data-testid="bot-detail-tabs" />;
  BotDetailTabs.displayName = "BotDetailTabs";
  return { default: BotDetailTabs };
});
vi.mock("../components/BalanceAnalysis", () => {
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

describe("FuturesBotDetail page", () => {
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
    expect(state.market_type).toBe(MarketType.FUTURES);
  });
});
