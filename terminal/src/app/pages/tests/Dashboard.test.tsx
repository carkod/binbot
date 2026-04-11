import "@testing-library/jest-dom";
import { screen as rtlScreen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import DashboardPage from "../Dashboard";
import { SpinnerContext } from "../../Layout";
import { renderWithProviders } from "../../../utils/test-utils";

vi.mock("../../../features/balanceApiSlice", () => ({
  useGetBalanceQuery: vi.fn(() => ({
    data: {
      balances: {},
      fiat_available: 5,
      fiat_currency: "USDC",
      estimated_total_fiat: 110,
    },
    isLoading: false,
  })),
  useGetBenchmarkQuery: vi.fn(() => ({
    data: {
      benchmarkData: {
        fiat: [100, 105],
        btc: [70000, 71000],
        dates: ["2026-04-10", "2026-04-11"],
      },
      percentageSeries: {
        fiatSeries: [4.76],
        btcSeries: [1.41],
        datesSeries: ["2026-04-11"],
      },
      portfolioStats: {
        pnl: 0.05,
        sharpe: -3.12,
        btc_sharpe: 1.27,
      },
    },
    isLoading: false,
  })),
}));

vi.mock("../../../features/bots/botsApiSlice", () => ({
  useGetBotsQuery: vi.fn(() => ({
    data: {
      bots: {
        ids: [],
      },
    },
    isLoading: false,
  })),
}));

vi.mock("../../../features/marketApiSlice", () => ({
  useAdSeriesQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock("../../filter-gainers-losers", () => ({
  useFilteredGainerLosers: vi.fn(() => ({
    combined: [],
    isLoading: false,
  })),
  useFilteredFuturesRankings: vi.fn(() => ({
    combined: [],
    isLoading: false,
  })),
}));

vi.mock("../../components/GainersLosers", () => ({
  default: () => <div>GainersLosers</div>,
}));

vi.mock("../../components/PortfolioBenchmark", () => ({
  default: () => <div>PortfolioBenchmarkChart</div>,
}));

vi.mock("../../components/AdrCard", () => ({
  default: () => <div>AdrCard</div>,
}));

describe("Dashboard page", () => {
  it("renders BTC sharpe in the risk efficiency section", () => {
    renderWithProviders(
      <MemoryRouter>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <DashboardPage />
        </SpinnerContext.Provider>
      </MemoryRouter>,
    );

    expect(
      rtlScreen.getByText("(How efficient are we with risk?)"),
    ).toBeInTheDocument();
    expect(rtlScreen.getByText("1.27 BTC")).toBeInTheDocument();
  });
});
