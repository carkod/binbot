import React from "react";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router";
import BotDetail from "../BotDetail";
import { store } from "../../store";
import { vi } from "vitest";
import { render, screen as rtlScreen, waitFor } from "@testing-library/react";
import { singleBot } from "../../../features/bots/botInitialState";

const mockUseGetSingleBotQuery = vi.hoisted(() => vi.fn());

vi.mock("../../../features/bots/botsApiSlice", async () => ({
  ...(await vi.importActual("../../../features/bots/botsApiSlice")),
  useGetSingleBotQuery: mockUseGetSingleBotQuery,
}));

vi.mock("../../../features/balanceApiSlice", async () => ({
  ...(await vi.importActual("../../../features/balanceApiSlice")),
  useGetBalanceQuery: vi.fn(() => ({ data: undefined, isLoading: false })),
}));

vi.mock("../../../features/symbolsApiSlice", async () => ({
  ...(await vi.importActual("../../../features/symbolsApiSlice")),
  useGetSymbolsQuery: vi.fn(() => ({ data: [] })),
}));

vi.mock("../../components/ChartContainer", () => {
  const ChartContainer = (_props: any) => <div data-testid="chart-container" />;
  ChartContainer.displayName = "ChartContainer";
  return { default: ChartContainer };
});
vi.mock("../../components/BotInfo", () => {
  const BotInfo = (_props: any) => <div data-testid="bot-info" />;
  BotInfo.displayName = "BotInfo";
  return { default: BotInfo };
});
vi.mock("../../components/LogsInfo", () => {
  const LogsInfo = (_props: any) => <div data-testid="logs-info" />;
  LogsInfo.displayName = "LogsInfo";
  return { default: LogsInfo };
});
vi.mock("../../components/BotDetailTabs", () => {
  const BotDetailTabs = (_props: any) => <div data-testid="bot-detail-tabs" />;
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

// Mock SpinnerContext if import fails
const SpinnerContext = React.createContext({
  spinner: false,
  setSpinner: () => {},
});

describe("BotDetail page", () => {
  beforeEach(() => {
    mockUseGetSingleBotQuery.mockReturnValue({
      data: { bot: { ...singleBot, id: "123" } },
      isLoading: false,
    });
  });

  it("renders without crashing", () => {
    const { container } = render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/123"]}>
            <Routes>
              <Route path="/bots/:id" element={<BotDetail />} />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );
    expect(container.querySelector(".content")).not.toBeNull();
    expect(rtlScreen.getByTestId("chart-container")).toBeTruthy();
  });

  it("shows BotInfo and BotDetailTabs when bot and id are present", async () => {
    render(
      <Provider store={store}>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <MemoryRouter initialEntries={["/bots/123"]}>
            <Routes>
              <Route path="/bots/:id" element={<BotDetail />} />
            </Routes>
          </MemoryRouter>
        </SpinnerContext.Provider>
      </Provider>,
    );
    await waitFor(() => {
      expect(rtlScreen.getByTestId("bot-info")).toBeTruthy();
    });
    expect(rtlScreen.getByTestId("bot-detail-tabs")).toBeTruthy();
  });
});
