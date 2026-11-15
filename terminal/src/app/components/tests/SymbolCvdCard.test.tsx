import "@testing-library/jest-dom";
import { render, screen as testingScreen } from "@testing-library/react";
import { vi } from "vitest";
import SymbolCvdCard from "../SymbolCvdCard";
import { useCvdSymbolQuery } from "../../../features/marketApiSlice";

vi.mock("../../../features/marketApiSlice", () => ({
  useCvdSymbolQuery: vi.fn(),
}));
vi.mock("../LivePlotlyChart", () => ({
  default: ({ data, layout }: { data: unknown; layout: unknown }) => (
    <div data-testid="chart">{JSON.stringify({ data, layout })}</div>
  ),
}));

const query = vi.mocked(useCvdSymbolQuery);
const point = {
  timestamp: "2026-11-15T10:00:00Z",
  buy: 123.12345678,
  sell: 23,
  cvd: 100.12345678,
  expected_symbols: 1,
  covered_symbols: 1,
  observed_minutes: 1,
  complete: true,
  gap: false,
  current: false,
  universe_changed: false,
};
const result = {
  source: "kucoin_futures",
  symbol: "SOLUSDTM",
  data: [point],
  reset_at: "2026-11-15T10:00:00Z",
  updated_at: "2026-11-15T10:15:00Z",
  stale: false,
  partial: false,
};
function respond(response: Record<string, unknown>) {
  query.mockReturnValue({
    refetch: vi.fn(),
    isFetching: false,
    isError: false,
    ...response,
  } as ReturnType<typeof useCvdSymbolQuery>);
}

describe("stored symbol CVD", () => {
  it("loads central history with symbol polling and preserves exact hover values", () => {
    respond({ currentData: result });
    render(<SymbolCvdCard symbol="SOLUSDTM" enabled />);
    expect(query).toHaveBeenCalledWith(
      "SOLUSDTM",
      expect.objectContaining({
        skip: false,
        pollingInterval: 30_000,
        refetchOnMountOrArgChange: true,
      }),
    );
    const {
      data: [trace],
      layout,
    } = JSON.parse(testingScreen.getByTestId("chart").textContent);
    expect(trace.y).toEqual([100.12345678]);
    expect(trace.text[0]).toContain("123.12345678 USDT");
    expect(trace.text[0]).toContain("100.12345678 USDT");
    expect(layout.xaxis.title.text).toContain("1-minute");
    expect(
      testingScreen.getByText(/Rolling 15-minute window/),
    ).toHaveTextContent(new Date(result.reset_at).toISOString());
    expect(
      testingScreen.getByText(/SOLUSDTM · KuCoin futures/),
    ).toBeInTheDocument();
  });

  it("shows loading, empty and failed states independently of the order book", () => {
    respond({ isFetching: true });
    const { rerender } = render(<SymbolCvdCard symbol="SOLUSDTM" enabled />);
    expect(testingScreen.getByRole("status")).toHaveTextContent(
      "Loading SOLUSDTM CVD",
    );
    respond({ currentData: { ...result, data: [] } });
    rerender(<SymbolCvdCard symbol="SOLUSDTM" enabled />);
    expect(
      testingScreen.getByText(/no observations yet for SOLUSDTM/),
    ).toBeInTheDocument();
    respond({ isError: true });
    rerender(<SymbolCvdCard symbol="SOLUSDTM" enabled />);
    expect(testingScreen.getByRole("alert")).toHaveTextContent(
      "could not be refreshed",
    );
  });

  it("uses currentData so changing bots shows the requested symbol's loading state", () => {
    respond({ currentData: result, data: result });
    const { rerender } = render(<SymbolCvdCard symbol="SOLUSDTM" enabled />);
    expect(testingScreen.getByTestId("chart")).toBeInTheDocument();
    respond({ data: result, isFetching: true });
    rerender(<SymbolCvdCard symbol="XBTUSDTM" enabled />);
    expect(testingScreen.getByRole("status")).toHaveTextContent(
      "Loading XBTUSDTM CVD",
    );
    expect(query).toHaveBeenLastCalledWith(
      "XBTUSDTM",
      expect.objectContaining({ skip: false }),
    );
  });

  it("keeps saved data visible through stale/error states and breaks partial/multiplier gaps", () => {
    respond({
      currentData: {
        ...result,
        stale: true,
        partial: true,
        data: [
          point,
          {
            ...point,
            timestamp: "2026-11-15T10:01:00Z",
            cvd: null,
            buy: null,
            sell: null,
            gap: true,
            complete: false,
            covered_symbols: 0,
          },
          {
            ...point,
            timestamp: "2026-11-15T10:02:00Z",
            cvd: 150,
            current: true,
            complete: false,
            gap: true,
            universe_changed: true,
          },
        ],
      },
      isError: true,
    });
    render(<SymbolCvdCard symbol="SOLUSDTM" enabled />);
    expect(testingScreen.getByText(/checkpoint is stale/)).toBeInTheDocument();
    expect(testingScreen.getByText(/Partial coverage:/)).toBeInTheDocument();
    expect(testingScreen.getByRole("alert")).toBeInTheDocument();
    const {
      data: [trace],
    } = JSON.parse(testingScreen.getByTestId("chart").textContent);
    expect(trace.y).toEqual([100.12345678, null, null, null, 150]);
    expect(trace.connectgaps).toBe(false);
    expect(trace.marker.symbol.at(-1)).toBe("diamond-open");
    expect(trace.text.at(-1)).toContain("Current interval (partial)");
    expect(trace.text.at(-1)).toContain("Contract multiplier changed");
  });

  it("waits for an enabled selected symbol", () => {
    respond({});
    const { rerender } = render(<SymbolCvdCard symbol="" enabled />);
    expect(testingScreen.getByText("Enter a symbol")).toBeInTheDocument();
    expect(query).toHaveBeenLastCalledWith(
      "",
      expect.objectContaining({ skip: true }),
    );
    rerender(<SymbolCvdCard symbol="SOLUSDTM" enabled={false} />);
    expect(query).toHaveBeenLastCalledWith(
      "SOLUSDTM",
      expect.objectContaining({ skip: true }),
    );
  });
});
