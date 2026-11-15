import "@testing-library/jest-dom";
import { render, screen as testingScreen } from "@testing-library/react";
import { vi } from "vitest";
import TradeFlowCard from "../TradeFlowCard";

vi.mock("../PlotlyChart", () => ({
  default: ({ data }: { data: unknown }) => (
    <div data-testid="cvd-chart">{JSON.stringify(data)}</div>
  ),
}));

describe("persisted CVD chart", () => {
  it("preserves the observed cumulative sum and breaks the line at missing coverage", () => {
    render(
      <TradeFlowCard
        kind="cvd"
        enabled
        status="live"
        restarted
        buckets={[
          { timestamp: 1_790_000_040_000, buy: 100, sell: 0 },
          { timestamp: 1_790_000_220_000, buy: 40, sell: 0, gapBefore: true },
        ]}
      />,
    );
    const trace = JSON.parse(
      testingScreen.getByTestId("cvd-chart").textContent,
    )[0];
    expect(trace.y).toEqual([100, null, 140]);
    expect(trace.connectgaps).toBe(false);
    expect(
      testingScreen.getByText(/Trades during time away/),
    ).toBeInTheDocument();
  });

  it("shows saved observations while reconnecting and warns when saving fails", () => {
    render(
      <TradeFlowCard
        kind="cvd"
        enabled
        status="connecting"
        restarted
        storageError
        buckets={[{ timestamp: 1_790_000_040_000, buy: 100, sell: 0 }]}
      />,
    );
    expect(testingScreen.getByTestId("cvd-chart")).toBeInTheDocument();
    expect(
      testingScreen.getByText(/Browser history storage unavailable/),
    ).toBeInTheDocument();
    expect(
      testingScreen.getByText(/Connecting to live trades/),
    ).toBeInTheDocument();
  });
});
