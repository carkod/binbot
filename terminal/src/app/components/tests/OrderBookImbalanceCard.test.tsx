import "@testing-library/jest-dom";
import { act, render, screen as testingScreen } from "@testing-library/react";
import { vi } from "vitest";
import OrderBookImbalanceCard from "../OrderBookImbalanceCard";
import type { ObiSnapshot } from "../../../features/kucoinLiquidity";
import { OBI_WINDOW_MS } from "../../../features/kucoinLiquidity";

vi.mock("../PlotlyChart", () => ({
  default: ({ data, layout }: { data: unknown; layout: unknown }) => (
    <div data-testid="obi-chart" data-layout={JSON.stringify(layout)}>
      {JSON.stringify(data)}
    </div>
  ),
}));

const now = 1_790_000_000_000;
const snapshot: ObiSnapshot = {
  spreadRatio: 0.0008,
  bidDepth: 30_000,
  askDepth: 18_000,
  timestamp: now,
  obi: 0.25,
  liquidity: "High liquidity",
  multiplier: 1,
};
const props = {
  enabled: true,
  isFetching: false,
  isError: false,
  onRetry: vi.fn(),
};

describe("OBI chart card", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(now);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("places a green liquidity badge beside the heading and charts OBI as a percentage", () => {
    render(<OrderBookImbalanceCard {...props} snapshot={snapshot} />);
    const badge = testingScreen.getByText("High liquidity");
    expect(badge).toHaveClass("badge", "bg-success");
    expect(badge.closest("h5")).toHaveTextContent("Order Book Imbalance (OBI)");
    const trace = JSON.parse(
      testingScreen.getByTestId("obi-chart").textContent,
    )[0];
    expect(trace.y).toEqual([25]);
    const layout = JSON.parse(
      testingScreen.getByTestId("obi-chart").getAttribute("data-layout"),
    );
    expect(layout.yaxis.range).toEqual([-100, 100]);
    expect(layout.xaxis.range).toEqual([
      new Date(now - OBI_WINDOW_MS).toISOString(),
      new Date(now).toISOString(),
    ]);
  });

  it("uses the danger color for low liquidity", () => {
    render(
      <OrderBookImbalanceCard
        {...props}
        snapshot={{ ...snapshot, liquidity: "Low liquidity" }}
      />,
    );
    expect(testingScreen.getByText("Low liquidity")).toHaveClass(
      "badge",
      "bg-danger",
    );
  });

  it("keeps historical points on failure and breaks the line across missed polls", () => {
    const { rerender } = render(
      <OrderBookImbalanceCard {...props} snapshot={snapshot} />,
    );
    rerender(<OrderBookImbalanceCard {...props} isError snapshot={snapshot} />);
    expect(testingScreen.queryByText("High liquidity")).not.toBeInTheDocument();
    expect(testingScreen.getByTestId("obi-chart")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(60_000));
    rerender(
      <OrderBookImbalanceCard
        {...props}
        snapshot={{ ...snapshot, timestamp: now + 60_000, obi: -0.5 }}
      />,
    );
    const trace = JSON.parse(
      testingScreen.getByTestId("obi-chart").textContent,
    )[0];
    expect(trace.y).toEqual([25, null, -50]);
    expect(trace.connectgaps).toBe(false);
  });

  it("removes history once it falls outside the time window", () => {
    render(<OrderBookImbalanceCard {...props} snapshot={snapshot} />);
    act(() => vi.advanceTimersByTime(OBI_WINDOW_MS + 15_000));
    expect(testingScreen.queryByTestId("obi-chart")).not.toBeInTheDocument();
  });
});
