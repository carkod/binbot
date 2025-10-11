import React from "react";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import BotDetail from "../BotDetail";
import { store } from "../../store";
import { vi } from "vitest";
import { render } from "@testing-library/react";
// import { vi } from "vitest"; // Commented out for clarity
// Place mocks here, after imports, before any usage
vi.mock("../components/ChartContainer", () => {
  const ChartContainer = () => <div data-testid="chart-container" />;
  ChartContainer.displayName = "ChartContainer";
  return { default: ChartContainer };
});
vi.mock("../components/BotInfo", () => {
  const BotInfo = () => <div data-testid="bot-info" />;
  BotInfo.displayName = "BotInfo";
  return { default: BotInfo };
});
vi.mock("../components/LogsInfo", () => {
  const LogsInfo = () => <div data-testid="logs-info" />;
  LogsInfo.displayName = "LogsInfo";
  return { default: LogsInfo };
});
vi.mock("../components/BotDetailTabs", () => {
  const BotDetailTabs = () => <div data-testid="bot-detail-tabs" />;
  BotDetailTabs.displayName = "BotDetailTabs";
  return { default: BotDetailTabs };
});
vi.mock("../components/BalanceAnalysis", () => {
  const BalanceAnalysis = () => <div data-testid="balance-analysis" />;
  BalanceAnalysis.displayName = "BalanceAnalysis";
  return { default: BalanceAnalysis };
});

// Mock SpinnerContext if import fails
const SpinnerContext = React.createContext({
  spinner: false,
  setSpinner: () => {},
});

describe("BotDetail page", () => {
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
  });

  it("shows BotInfo and BotDetailTabs when bot and id are present", () => {
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
    // Check for BotInfo by class or id
    expect(document.querySelector(".card-header")).not.toBeNull();
    // Check for BotDetailTabs by nav-tabs class
    expect(document.querySelector(".nav.nav-tabs")).not.toBeNull();
  });
});
