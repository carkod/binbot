import "@testing-library/jest-dom";
import { fireEvent } from "@testing-library/react";
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

const respond = (
  trades: unknown,
  extra: Record<string, unknown> = {},
  contractExtra: Record<string, unknown> = {},
) => {
  const refetchTrades = vi.fn();

  const refetchContract = vi.fn();

  vi.mocked(useFuturesTradesQuery).mockReturnValue({
    currentData: trades,
    refetch: refetchTrades,
    isFetching: false,
    isError: false,
    ...extra,
  } as ReturnType<typeof useFuturesTradesQuery>);
  vi.mocked(useFuturesContractQuery).mockReturnValue({
    refetch: refetchContract,
    currentData: { symbol: "SOLUSDTM", multiplier: 1 },
    isFetching: false,
    isError: false,
    ...contractExtra,
  } as ReturnType<typeof useFuturesContractQuery>);
  return { refetchTrades, refetchContract };
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

  it("retries a failed trade request", () => {
    const { refetchTrades, refetchContract } = respond(undefined, {
      isError: true,
    });

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByRole("alert")).toHaveTextContent(
      "SOLUSDTM trades could not be refreshed.",
    );
    fireEvent.click(testingScreen.getByRole("button", { name: "Retry" }));
    expect(refetchTrades).toHaveBeenCalledOnce();
    expect(refetchContract).not.toHaveBeenCalled();
  });

  it("shows loading while contract details are being fetched", () => {
    respond([], {}, { currentData: undefined, isFetching: true });

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByRole("status")).toHaveTextContent(
      "Loading SOLUSDTM trades…",
    );
  });

  it("recovers from a contract request failure without remounting the card", () => {
    const trades = [
      { tradeId: "a", side: "buy", price: 10, size: 5, timestamp: Date.now() },
    ];

    const { refetchTrades, refetchContract } = respond(
      trades,
      {},
      { currentData: undefined, isError: true },
    );

    const { rerender } = render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByRole("alert")).toHaveTextContent(
      "SOLUSDTM contract details could not be loaded.",
    );
    fireEvent.click(testingScreen.getByRole("button", { name: "Retry" }));
    expect(refetchContract).toHaveBeenCalledOnce();
    expect(refetchTrades).not.toHaveBeenCalled();

    respond(trades);
    rerender(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByText("1 trades")).toBeInTheDocument();
    expect(testingScreen.getByTestId("chart")).toBeInTheDocument();
  });

  it("retries both requests when trades and contract details fail", () => {
    const { refetchTrades, refetchContract } = respond(
      undefined,
      { isError: true },
      { currentData: undefined, isError: true },
    );

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);
    fireEvent.click(testingScreen.getByRole("button", { name: "Retry" }));

    expect(refetchTrades).toHaveBeenCalledOnce();
    expect(refetchContract).toHaveBeenCalledOnce();
  });

  it("disables retry until an in-flight request finishes", () => {
    respond(
      [],
      { isFetching: true },
      { currentData: undefined, isError: true },
    );

    render(<SymbolTradesCard symbol="SOLUSDTM" enabled />);

    expect(testingScreen.getByRole("button", { name: "Retry" })).toBeDisabled();
  });
});
