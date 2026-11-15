import "@testing-library/jest-dom";
import { screen as rtlScreen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import DashboardPage from "../Dashboard";
import { renderWithProviders } from "../../../utils/test-utils";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../../features/balanceApiSlice";
import { useGetBotsQuery } from "../../../features/bots/botsApiSlice";
import {
  useFastestMoversQuery,
  useGainersLosersAggregateQuery,
} from "../../../features/marketApiSlice";
import { useBtcCloseSeriesQuery } from "../../../features/kucoinApiSlice";
import { useFilteredFuturesRankings } from "../../hooks/useFilteredFuturesRankings";

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
}));

vi.mock("../../../features/marketApiSlice", () => ({
  useFastestMoversQuery: vi.fn(() => ({
    data: {
      source: "kucoin_futures",
      recorded_at: "2026-08-10T10:00:00Z",
      comparison_at: "2026-08-10T09:00:00Z",
      gainers: [],
      losers: [],
    },
    isLoading: false,
  })),
  useGainersLosersAggregateQuery: vi.fn(() => ({
    data: [
      {
        timestamp: "2026-08-10T10:00:00Z",
        gainer_magnitude: 30,
        loser_magnitude: 10,
        advancers: 30,
        decliners: 10,
      },
    ],
    isLoading: false,
  })),
}));

vi.mock("../../../features/kucoinApiSlice", async (importOriginal) => ({
  ...(await importOriginal()),
  useBtcCloseSeriesQuery: vi.fn(() => ({
    data: {
      symbol: "XBTUSDTM",
      interval: "15m",
      timestamp: ["2026-08-10T10:00:00Z"],
      close: [65000],
    },
    isLoading: false,
  })),
}));

vi.mock("../../hooks/useFilteredFuturesRankings", () => ({
  useFilteredFuturesRankings: vi.fn(() => ({
    combined: [],
    isLoading: false,
  })),
}));

vi.mock("../../components/GainersLosers", () => ({
  default: () => <div>GainersLosers</div>,
}));

vi.mock("../../components/FastestMovers", () => ({
  default: () => <div>FastestMovers</div>,
}));

vi.mock("../../components/PortfolioBenchmark", () => ({
  default: () => <div>PortfolioBenchmarkChart</div>,
}));

vi.mock("../../components/GainersLosersHistoryCard", () => ({
  default: () => <div>GainersLosersHistoryCard</div>,
}));

vi.mock("../../components/BitcoinPriceCard", () => ({
  default: () => <div>BitcoinPriceCard</div>,
}));

vi.mock("../../components/AggregateCvdCard", () => ({
  default: () => <div>AggregateCvdCard</div>,
}));

describe("Dashboard page", () => {
  afterEach(() => vi.unstubAllEnvs());
  const renderDashboard = () =>
    renderWithProviders(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

  it("groups account and market cards under headings on the dashboard background", () => {
    renderDashboard();
    const account = rtlScreen.getByRole("region", { name: "Account overview" });
    const market = rtlScreen.getByRole("region", { name: "Market analysis" });
    expect(account).toContainElement(
      rtlScreen.getByText("PortfolioBenchmarkChart"),
    );
    expect(account).toContainElement(rtlScreen.getByText("Total Balance"));
    expect(market).toContainElement(rtlScreen.getByText("FastestMovers"));
    expect(market).toContainElement(
      rtlScreen.getByText("GainersLosersHistoryCard"),
    );
    expect(market).toContainElement(rtlScreen.getByText("BitcoinPriceCard"));
    for (const name of [
      "Account overview",
      "Market analysis",
      "Order book aggregation",
    ]) {
      expect(
        rtlScreen.getByRole("heading", { name, level: 2 }).parentElement,
      ).toHaveAttribute("aria-labelledby");
    }
  });

  it("shows enabled market CVD alongside the market trend charts", () => {
    vi.stubEnv("VITE_MARKET_CVD_ENABLED", "true");
    renderDashboard();
    expect(
      rtlScreen.getByRole("region", { name: "Market analysis" }),
    ).toContainElement(rtlScreen.getByText("AggregateCvdCard"));
  });

  it("renders BTC sharpe in the risk efficiency section", () => {
    renderDashboard();

    expect(
      rtlScreen.getByText("(How efficient are we with risk?)"),
    ).toBeInTheDocument();
    expect(rtlScreen.getByText("110 USDC")).toBeInTheDocument();
    expect(rtlScreen.getByText("1.27 BTC")).toBeInTheDocument();
  });

  it("renders both market trend charts in half-width desktop columns", () => {
    renderDashboard();

    expect(
      rtlScreen.getByText("GainersLosersHistoryCard").closest(".col-lg-6"),
    ).toBeInTheDocument();
    expect(
      rtlScreen.getByText("BitcoinPriceCard").closest(".col-lg-6"),
    ).toBeInTheDocument();
  });

  it("reveals a loaded chart once and keeps it visible on refresh", async () => {
    vi.mocked(useGetBenchmarkQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGetBenchmarkQuery>);

    const { rerender } = renderDashboard();

    expect(
      rtlScreen.getByRole("status", {
        name: "Loading portfolio benchmark...",
      }),
    ).toBeInTheDocument();
    expect(rtlScreen.queryByText("PortfolioBenchmarkChart")).toBeNull();
    expect(rtlScreen.getByText("BitcoinPriceCard")).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    const chart = rtlScreen.getByText("PortfolioBenchmarkChart");
    const reveal = chart.parentElement;
    expect(reveal).toHaveStyle({ opacity: "0" });
    await waitFor(() => {
      expect(reveal).toHaveStyle({ opacity: "1", transform: "none" });
    });
    expect(
      rtlScreen.queryByRole("status", {
        name: "Loading portfolio benchmark...",
      }),
    ).toBeNull();

    rerender(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(rtlScreen.getByText("PortfolioBenchmarkChart")).toBe(chart);
    expect(reveal).toHaveStyle({ opacity: "1", transform: "none" });
  });

  it("renders loading spinners inside each card without a page overlay", () => {
    vi.mocked(useGetBalanceQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGetBalanceQuery>);
    vi.mocked(useGetBenchmarkQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGetBenchmarkQuery>);
    vi.mocked(useGetBotsQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGetBotsQuery>);
    vi.mocked(useFastestMoversQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useFastestMoversQuery>);
    vi.mocked(useFilteredFuturesRankings).mockReturnValueOnce({
      combined: [],
      isLoading: true,
    });
    vi.mocked(useGainersLosersAggregateQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGainersLosersAggregateQuery>);
    vi.mocked(useBtcCloseSeriesQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useBtcCloseSeriesQuery>);

    renderDashboard();

    const spinners = rtlScreen.getAllByRole("status");

    expect(spinners).toHaveLength(9);
    spinners.forEach((spinner) => {
      expect(spinner.closest(".card")).toBeInTheDocument();
    });
    expect(
      rtlScreen.getByRole("status", { name: "Loading total balance..." }),
    ).toBeInTheDocument();

    expect(document.querySelector('[style*="position: absolute"]')).toBeNull();
  });
});
