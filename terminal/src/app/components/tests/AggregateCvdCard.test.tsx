import "@testing-library/jest-dom";
import { render, screen as testingScreen } from "@testing-library/react";
import { vi } from "vitest";
import AggregateCvdCard from "../AggregateCvdCard";
import { useCvdAggregateQuery } from "../../../features/marketApiSlice";

vi.mock("../../../features/marketApiSlice", () => ({
  useCvdAggregateQuery: vi.fn(),
}));
vi.mock("../LivePlotlyChart", () => ({
  default: ({ data }: { data: unknown }) => (
    <div data-testid="chart">{JSON.stringify(data)}</div>
  ),
}));
const query = vi.mocked(useCvdAggregateQuery);
const point = {
  timestamp: "2026-11-15T10:00:00Z",
  buy: 123.12345678,
  sell: 23,
  cvd: 100.12345678,
  expected_symbols: 717,
  covered_symbols: 717,
  observed_minutes: 15,
  complete: true,
  gap: false,
  current: false,
  universe_changed: false,
};
const result = {
  source: "kucoin_futures",
  data: [point],
  reset_at: "2026-11-08T10:00:00Z",
  updated_at: "2026-11-15T10:15:00Z",
  stale: false,
  partial: false,
};
function respond(response: Record<string, unknown>) {
  query.mockReturnValue({
    refetch: vi.fn(),
    isLoading: false,
    isError: false,
    ...response,
  } as ReturnType<typeof useCvdAggregateQuery>);
}

describe("market CVD card", () => {
  it("shows loading, empty and fetch failures", () => {
    respond({ isLoading: true });
    const { rerender } = render(<AggregateCvdCard />);
    expect(testingScreen.getByRole("status")).toHaveTextContent(
      "Loading market CVD",
    );
    respond({ data: { ...result, data: [] } });
    rerender(<AggregateCvdCard />);
    expect(testingScreen.getByText(/no observations yet/)).toBeInTheDocument();
    respond({ isError: true });
    rerender(<AggregateCvdCard />);
    expect(testingScreen.getByRole("alert")).toHaveTextContent(
      "could not be refreshed",
    );
  });

  it("keeps saved data visible during stale/error states and displays coverage", () => {
    respond({ data: { ...result, stale: true, partial: true }, isError: true });
    render(<AggregateCvdCard />);
    expect(testingScreen.getByTestId("chart")).toBeInTheDocument();
    expect(testingScreen.getByText(/checkpoint is stale/)).toBeInTheDocument();
    expect(testingScreen.getByText(/Partial coverage:/)).toBeInTheDocument();
    expect(
      testingScreen.getByText(/CVD starts at zero at/),
    ).toBeInTheDocument();
    expect(query).toHaveBeenCalledWith(undefined, { pollingInterval: 60_000 });
  });

  it("preserves precise hover values and breaks partial and changed universes", () => {
    respond({
      data: {
        ...result,
        partial: true,
        data: [
          point,
          {
            ...point,
            timestamp: "2026-11-15T10:15:00Z",
            cvd: null,
            gap: true,
            complete: false,
            buy: null,
            sell: null,
            covered_symbols: 0,
          },
          {
            ...point,
            timestamp: "2026-11-15T10:30:00Z",
            cvd: 150,
            current: true,
            complete: false,
            gap: true,
            universe_changed: true,
          },
        ],
      },
    });
    render(<AggregateCvdCard />);
    const trace = JSON.parse(testingScreen.getByTestId("chart").textContent)[0];
    expect(trace.y).toEqual([100.12345678, null, null, null, 150]);
    expect(trace.customdata[0]).toEqual([
      123.12345678,
      23,
      717,
      717,
      "Complete",
      "",
    ]);
    expect(trace.connectgaps).toBe(false);
    expect(trace.marker.symbol.at(-1)).toBe("diamond-open");
    expect(trace.customdata.at(-1)).toContain("Current interval (partial)");
  });
});
