import "@testing-library/jest-dom";
import { screen as rtlScreen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import DashboardPage from "../Dashboard";
import { renderWithProviders } from "../../../utils/test-utils";
import { useGetSignalsQuery } from "../../../features/signalsApiSlice";
import {
  useGetBalanceQuery,
  useGetBenchmarkQuery,
} from "../../../features/balanceApiSlice";
import {
  useGetAlgoRankingQuery,
  useGetBotsQuery,
} from "../../../features/bots/botsApiSlice";
import { useMarketBreadthSeriesQuery } from "../../../features/marketApiSlice";
import { useBtcCloseSeriesQuery } from "../../../features/kucoinApiSlice";
import { useBinquantStrategyNames } from "../../hooks/useBinquantStrategyNames";
import { useFilteredFuturesRankings } from "../../hooks/useFilteredFuturesRankings";
import { useFilteredGainerLosers } from "../../hooks/useFilteredGainerLosers";

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
  useMarketBreadthSeriesQuery: vi.fn(() => ({
    data: {
      timestamp: ["2026-08-10T10:00:00Z"],
      market_breadth: [0.2],
      market_breadth_ma: [0.15],
      strength_index: [0.1],
    },
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

vi.mock("../../../features/signalsApiSlice", () => ({
  useGetSignalsQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock("../../hooks/useFilteredGainerLosers", () => ({
  useFilteredGainerLosers: vi.fn(() => ({
    combined: [],
    isLoading: false,
  })),
}));

vi.mock("../../hooks/useFilteredFuturesRankings", () => ({
  useFilteredFuturesRankings: vi.fn(() => ({
    combined: [],
    isLoading: false,
  })),
}));

vi.mock("../../hooks/useBinquantStrategyNames", () => ({
  useBinquantStrategyNames: vi.fn(() => ({
    strategyNames: new Set<string>(),
    isLoading: false,
    error: undefined,
  })),
}));

vi.mock("../../components/GainersLosers", () => ({
  default: () => <div>GainersLosers</div>,
}));

vi.mock("../../components/PortfolioBenchmark", () => ({
  default: () => <div>PortfolioBenchmarkChart</div>,
}));

vi.mock("../../components/MarketBreadthCard", () => ({
  default: () => <div>MarketBreadthCard</div>,
}));

vi.mock("../../components/BitcoinPriceCard", () => ({
  default: () => <div>BitcoinPriceCard</div>,
}));

describe("Dashboard page", () => {
  const renderDashboard = () =>
    renderWithProviders(
      <MemoryRouter>
        <DashboardPage />
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

  it("renders both market trend charts in half-width desktop columns", () => {
    renderDashboard();

    expect(
      rtlScreen.getByText("MarketBreadthCard").closest(".col-lg-6"),
    ).toBeInTheDocument();
    expect(
      rtlScreen.getByText("BitcoinPriceCard").closest(".col-lg-6"),
    ).toBeInTheDocument();
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
    vi.mocked(useGetAlgoRankingQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGetAlgoRankingQuery>);
    vi.mocked(useFilteredGainerLosers).mockReturnValueOnce({
      combined: [],
      isLoading: true,
      futuresRankings: [],
      loadingFutures: true,
    });
    vi.mocked(useFilteredFuturesRankings).mockReturnValueOnce({
      combined: [],
      isLoading: true,
    });
    vi.mocked(useMarketBreadthSeriesQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useMarketBreadthSeriesQuery>);
    vi.mocked(useBtcCloseSeriesQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useBtcCloseSeriesQuery>);
    vi.mocked(useGetSignalsQuery).mockReturnValueOnce({
      isLoading: true,
    } as unknown as ReturnType<typeof useGetSignalsQuery>);
    vi.mocked(useBinquantStrategyNames).mockReturnValueOnce({
      strategyNames: new Set(),
      isLoading: true,
      error: undefined,
    });

    renderDashboard();

    const spinners = rtlScreen.getAllByRole("status");

    expect(spinners).toHaveLength(11);
    spinners.forEach((spinner) => {
      expect(spinner.closest(".card")).toBeInTheDocument();
    });
    expect(
      rtlScreen.getByRole("status", { name: "Loading total balance..." }),
    ).toBeInTheDocument();
    expect(
      rtlScreen.getByRole("status", { name: "Loading algorithm ranking..." }),
    ).toBeInTheDocument();
    expect(document.querySelector('[style*="position: absolute"]')).toBeNull();
  });

  it("removes symbol concentration from the dashboard", () => {
    renderDashboard();

    expect(
      rtlScreen.queryByText("Symbol concentration"),
    ).not.toBeInTheDocument();
  });

  it("filters algorithm ranking to strategies currently in Binquant", () => {
    vi.mocked(useGetAlgoRankingQuery).mockReturnValueOnce({
      data: [
        { name: "top_gainer_early_momentum", count: 3, bot_profit: 9 },
        { name: "retired_strategy", count: 10, bot_profit: 20 },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useGetAlgoRankingQuery>);
    vi.mocked(useBinquantStrategyNames).mockReturnValueOnce({
      strategyNames: new Set(["top_gainer_early_momentum"]),
      isLoading: false,
      error: undefined,
    });

    renderDashboard();

    const algorithmCard = rtlScreen
      .getByText("Algorithm Ranking")
      .closest(".card");

    expect(
      within(algorithmCard as HTMLElement).getByText(
        "top_gainer_early_momentum",
      ),
    ).toBeInTheDocument();
    expect(
      within(algorithmCard as HTMLElement).queryByText("retired_strategy"),
    ).not.toBeInTheDocument();
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
    } as unknown as ReturnType<typeof useGetSignalsQuery>);

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
