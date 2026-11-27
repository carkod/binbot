import "@testing-library/jest-dom";
import { vi } from "vitest";
import {
  useFuturesContractQuery,
  useFuturesTradesQuery,
} from "../../../features/kucoinApiSlice";
import { render, screen as testingScreen } from "../../../utils/render";
import SymbolTradesCard from "../SymbolTradesCard";

vi.mock("../../../features/kucoinApiSlice", () => ({
  useFuturesTradesQuery: vi.fn(),
  useFuturesContractQuery: vi.fn(),
}));
vi.mock("../LivePlotlyChart", () => ({
  default: (props: { data: unknown }) => (
    <div data-testid="chart">{JSON.stringify(props.data)}</div>
  ),
}));

const respond = (trades: unknown, extra: Record<string, unknown> = {}) => {
  vi.mocked(useFuturesTradesQuery).mockReturnValue({
    currentData: trades,
    refetch: vi.fn(),
    isFetching: false,
    isError: false,
    ...extra,
  } as ReturnType<typeof useFuturesTradesQuery>);
  vi.mocked(useFuturesContractQuery).mockReturnValue({
    refetch: vi.fn(),
    currentData: { symbol: "SOLUSDTM", multiplier: 1 },
  } as ReturnType<typeof useFuturesContractQuery>);
};

describe("symbol market trades", () => {
  it("summarizes taker buy and sell notional from the last 5 minutes only", () => {
    const now = Date.now();

    respond([
      { tradeId: "a", side: "buy", price: 10, size: 5, timestamp: now - 2_000 },
      {
        tradeId: "b",
        side: "sell",
        price: 10,
        size: 2,
        timestamp: now - 1_000,
      },
      {
        tradeId: "c",
        side: "buy",
        price: 10,
        size: 99,
        timestamp: now - 400_000,
      },
    ]);

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByText("2 trades")).toBeInTheDocument();
    expect(testingScreen.getByTestId("chart")).toBeInTheDocument();
  });

  it("says when the contract had no trades in the last 5 minutes", () => {
    respond([
      {
        tradeId: "old",
        side: "buy",
        price: 10,
        size: 5,
        timestamp: Date.now() - 400_000,
      },
    ]);

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(
      testingScreen.getByText("No trades for SOLUSDTM in the last 5 minutes."),
    ).toBeInTheDocument();
  });

  it("shows an alert when the trade request fails", () => {
    respond(undefined, { isError: true });

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByRole("alert")).toHaveTextContent(
      "SOLUSDTM trades could not be refreshed.",
    );
  });
});
