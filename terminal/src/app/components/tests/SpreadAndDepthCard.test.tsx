import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import { vi } from "vitest";
import SpreadAndDepthCard from "../SpreadAndDepthCard";
import {
  OBI_WINDOW_MS,
  type ObiSnapshot,
} from "../../../features/kucoinLiquidity";

vi.mock("../PlotlyChart", () => ({
  default: ({ data, layout }: { data: unknown; layout: unknown }) => (
    <div data-testid="spread-depth-chart" data-layout={JSON.stringify(layout)}>
      {JSON.stringify(data)}
    </div>
  ),
}));

const now = 1_790_000_000_000;
const snapshot: ObiSnapshot = {
  timestamp: now,
  obi: 0.2,
  liquidity: "High liquidity",
  multiplier: 0.001,
  spreadRatio: 0.0008,
  bidDepth: 30,
  askDepth: 20,
};
const props = {
  enabled: true,
  isFetching: false,
  isError: false,
  onRetry: vi.fn(),
};

describe("spread and nearby depth chart", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(now);
    props.onRetry.mockClear();
  });
  afterEach(() => vi.useRealTimers());

  it("charts USDT depth and percentage spread on separate axes", () => {
    render(<SpreadAndDepthCard {...props} snapshot={snapshot} />);
    const chart = testingScreen.getByTestId("spread-depth-chart");
    const traces = JSON.parse(chart.textContent);
    expect(traces.map(({ y }) => y)).toEqual([[30], [20], [0.08]]);
    expect(traces.map(({ name }) => name)).toEqual([
      "Bid depth",
      "Ask depth",
      "Spread",
    ]);
    expect(traces[2].yaxis).toBe("y2");
    const layout = JSON.parse(chart.getAttribute("data-layout"));
    expect(layout.yaxis.title.text).toBe("Nearby depth (USDT)");
    expect(layout.yaxis2.title.text).toBe("Spread (%)");
    expect(layout.xaxis.range).toEqual([
      new Date(now - OBI_WINDOW_MS).toISOString(),
      new Date(now).toISOString(),
    ]);
  });

  it("keeps measurements on failure and leaves gaps in all three traces", () => {
    const { rerender } = render(
      <SpreadAndDepthCard {...props} snapshot={snapshot} />,
    );
    rerender(<SpreadAndDepthCard {...props} snapshot={snapshot} isError />);
    fireEvent.click(testingScreen.getByRole("button", { name: "Retry" }));
    expect(props.onRetry).toHaveBeenCalledOnce();
    act(() => vi.advanceTimersByTime(60_000));
    rerender(
      <SpreadAndDepthCard
        {...props}
        snapshot={{ ...snapshot, timestamp: now + 60_000 }}
      />,
    );
    const traces = JSON.parse(
      testingScreen.getByTestId("spread-depth-chart").textContent,
    );
    expect(traces.map(({ y }) => y)).toEqual([
      [30, null, 30],
      [20, null, 20],
      [0.08, null, 0.08],
    ]);
    expect(traces.every(({ connectgaps }) => connectgaps === false)).toBe(true);
  });

  it("expires measurements after 15 minutes without new snapshots", () => {
    render(<SpreadAndDepthCard {...props} snapshot={snapshot} />);
    act(() => vi.advanceTimersByTime(OBI_WINDOW_MS + 15_000));
    expect(
      testingScreen.queryByTestId("spread-depth-chart"),
    ).not.toBeInTheDocument();
  });

  it("hides history when the selected symbol is being edited", () => {
    const { rerender } = render(
      <SpreadAndDepthCard {...props} snapshot={snapshot} />,
    );
    rerender(
      <SpreadAndDepthCard {...props} snapshot={snapshot} enabled={false} />,
    );
    expect(
      testingScreen.queryByTestId("spread-depth-chart"),
    ).not.toBeInTheDocument();
    expect(testingScreen.getByText("Enter a symbol")).toBeInTheDocument();
  });
});
