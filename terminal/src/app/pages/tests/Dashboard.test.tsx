import "@testing-library/jest-dom";
import { screen as rtlScreen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import DashboardPage from "../Dashboard";
import { SpinnerContext } from "../../Layout";
import { renderWithProviders } from "../../../utils/test-utils";
import { useGetSignalsQuery } from "../../../features/signalsApiSlice";

vi.mock("../../../features/balanceApiSlice", () => ({
  useGetBalanceQuery: vi.fn(() => ({
    data: {
      balances: {},
      fiat_available: 5,
      fiat_currency: "USDC",
      estimated_total_fiat: 110,
      total_deposit: 5,
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
  useGetAlgoRankingQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock("../../../features/marketApiSlice", () => ({
  useAdSeriesQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock("../../../features/signalsApiSlice", () => ({
  useGetSignalsQuery: vi.fn(() => ({
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
  const renderDashboard = () =>
    renderWithProviders(
      <MemoryRouter>
        <SpinnerContext.Provider
          value={{ spinner: false, setSpinner: vi.fn() }}
        >
          <DashboardPage />
        </SpinnerContext.Provider>
      </MemoryRouter>,
    );

  it("renders BTC sharpe in the risk efficiency section", () => {
    renderDashboard();

    expect(
      rtlScreen.getByText("(How efficient are we with risk?)"),
    ).toBeInTheDocument();
    expect(rtlScreen.getByText("110 USDC")).toBeInTheDocument();
    expect(rtlScreen.getByText("1.27 BTC")).toBeInTheDocument();
  });

  it("renders signals collapsed and ranked by algorithm count", () => {
    vi.mocked(useGetSignalsQuery).mockReturnValueOnce({
      data: [
        {
          id: 1,
          algorithm_name: "mean_reversion",
          symbol: "ETHUSDC",
          generated_at: "2026-05-01T09:00:00",
          direction: "long",
          autotrade: false,
          current_regime: "range",
          context: {},
          bot_params: {},
          indicators: {},
        },
        {
          id: 2,
          algorithm_name: "apex_flow",
          symbol: "BTCUSDC",
          generated_at: "2026-05-01T10:00:00",
          direction: "long",
          autotrade: true,
          current_regime: "bull",
          context: {},
          bot_params: {},
          indicators: {},
        },
        {
          id: 3,
          algorithm_name: "apex_flow",
          symbol: "SOLUSDC",
          generated_at: "2026-05-01T08:00:00",
          direction: "short",
          autotrade: false,
          current_regime: "bear",
          context: {},
          bot_params: {},
          indicators: {},
        },
      ],
      isLoading: false,
    } as ReturnType<typeof useGetSignalsQuery>);

    renderDashboard();

    const signalCard = rtlScreen.getByText("Signal Ranking").closest(".card");

    expect(signalCard).toBeInTheDocument();
    expect(
      within(signalCard as HTMLElement).getByText("1 May, 10:00"),
    ).toBeInTheDocument();
    expect(
      within(signalCard as HTMLElement).getByText("bull"),
    ).toBeInTheDocument();
    expect(
      within(signalCard as HTMLElement).queryByText("Symbol"),
    ).not.toBeInTheDocument();
    expect(
      within(signalCard as HTMLElement).queryByText("BTCUSDC"),
    ).not.toBeInTheDocument();

    const rows = within(signalCard as HTMLElement).getAllByRole("row");
    expect(within(rows[1]).getByText("apex_flow")).toBeInTheDocument();
    expect(within(rows[1]).getByText("2")).toBeInTheDocument();
    expect(within(rows[2]).getByText("mean_reversion")).toBeInTheDocument();
    expect(within(rows[2]).getByText("1")).toBeInTheDocument();
  });
});
