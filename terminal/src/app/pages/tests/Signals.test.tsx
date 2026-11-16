import "@testing-library/jest-dom";
import { vi } from "vitest";
import { useGetAlgoRankingQuery } from "../../../features/bots/botsApiSlice";
import { useGetSignalsQuery } from "../../../features/signalsApiSlice";
import { render, screen as rtlScreen, within } from "../../../utils/render";
import { useBinquantStrategyNames } from "../../hooks/useBinquantStrategyNames";
import SignalsPage from "../Signals";

vi.mock("../../../features/balanceApiSlice", () => ({
  useGetBalanceQuery: vi.fn(() => ({ data: { fiat_currency: "USDC" } })),
}));
vi.mock("../../../features/bots/botsApiSlice", () => ({
  useGetAlgoRankingQuery: vi.fn(() => ({ data: [], isLoading: false })),
}));
vi.mock("../../../features/signalsApiSlice", () => ({
  useGetSignalsQuery: vi.fn(() => ({ data: [], isLoading: false })),
}));
vi.mock("../../hooks/useBinquantStrategyNames", () => ({
  useBinquantStrategyNames: vi.fn(() => ({
    strategyNames: new Set<string>(),
    isLoading: false,
    error: undefined,
  })),
}));

describe("Signals page", () => {
  const renderSignals = () => render(<SignalsPage />);

  it("shows loading states for strategy and signal rankings", () => {
    vi.mocked(useGetAlgoRankingQuery).mockReturnValueOnce({
      isLoading: true,
      refetch: vi.fn(),
    } as ReturnType<typeof useGetAlgoRankingQuery>);
    vi.mocked(useGetSignalsQuery).mockReturnValueOnce({
      isLoading: true,
      refetch: vi.fn(),
    } as ReturnType<typeof useGetSignalsQuery>);
    renderSignals();
    expect(
      rtlScreen.getByRole("status", { name: "Loading strategy ranking..." }),
    ).toBeInTheDocument();
    expect(
      rtlScreen.getByRole("status", { name: "Loading signal ranking..." }),
    ).toBeInTheDocument();
  });

  it("shows a strategy directory error in the strategy ranking card", () => {
    vi.mocked(useBinquantStrategyNames).mockReturnValueOnce({
      strategyNames: new Set(),
      isLoading: false,
      error: "Unable to load Binquant strategies",
    });
    renderSignals();
    expect(rtlScreen.getByRole("alert")).toHaveTextContent(
      "Unable to load Binquant strategies",
    );
  });
  it("shows current Binquant strategies and all terminal bots in the ranking", () => {
    vi.mocked(useGetAlgoRankingQuery).mockReturnValueOnce({
      data: [
        { name: "top_gainer_early_momentum", count: 3, bot_profit: 9 },
        { name: "terminal", count: 7, bot_profit: 12 },
        { name: "retired_strategy", count: 10, bot_profit: 20 },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useGetAlgoRankingQuery>);
    vi.mocked(useBinquantStrategyNames).mockReturnValueOnce({
      strategyNames: new Set(["top_gainer_early_momentum"]),
      isLoading: false,
      error: undefined,
    });

    renderSignals();

    const algorithmCard = rtlScreen
      .getByText("Strategy ranking")
      .closest(".mantine-Card-root");

    expect(
      within(algorithmCard as HTMLElement).getByText(
        "top_gainer_early_momentum",
      ),
    ).toBeInTheDocument();
    expect(
      within(algorithmCard as HTMLElement).getByText("terminal"),
    ).toBeInTheDocument();
    expect(
      within(algorithmCard as HTMLElement).getByText("7"),
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

    renderSignals();

    const signalCard = rtlScreen
      .getByText("Signal Ranking")
      .closest(".mantine-Card-root");

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
