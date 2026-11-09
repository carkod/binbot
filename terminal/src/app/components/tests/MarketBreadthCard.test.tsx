import "@testing-library/jest-dom";
import { render, screen as rtlScreen } from "@testing-library/react";
import {
  beforeEach as beforeEachTest,
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
  vi,
} from "vitest";

type PlotlyTrace = {
  name?: string;
  x?: string[];
  y?: Array<number | null>;
  yaxis?: string;
  line?: { color?: string };
};

type PlotlyProps = {
  data: PlotlyTrace[];
  layout: {
    yaxis?: {
      title?: { text?: string; standoff?: number };
      zeroline?: boolean;
      range?: number[];
    };
    yaxis2?: unknown;
  };
};

const plotlyChartMock = vi.hoisted(() =>
  vi.fn((props: PlotlyProps) => (
    <div
      data-testid="plotly-chart"
      data-chart-props={JSON.stringify({
        data: props.data,
        layout: props.layout,
      })}
    />
  )),
);

vi.mock("../PlotlyChart", () => ({
  default: plotlyChartMock,
}));

import MarketBreadthCard from "../MarketBreadthCard";

const timestamps = [
  "2026-07-04 11:10:02",
  "2026-07-04 10:55:02",
  "2026-07-04 10:40:02",
  "2026-07-04 10:25:02",
  "2026-07-04 10:10:02",
];

// Newest first: the total rose 85 points over the last hour (4 samples).
const defaultProps = {
  cumulativeBreadth: [60, 40, 10, -5, -25],
  cumulativeBreadthEma: [12.4, 5.1, -2.3, -6.0, -8.0],
  timestamps,
};

const latestPlotlyProps = () => {
  const call =
    plotlyChartMock.mock.calls[plotlyChartMock.mock.calls.length - 1];
  expectValue(call).toBeDefined();

  return call[0] as PlotlyProps;
};

describeBlock("MarketBreadthCard", () => {
  beforeEachTest(() => {
    plotlyChartMock.mockClear();
  });

  testCase("shows a rising trend when the total is above its EMA", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    expectValue(rtlScreen.getByText("Trend: rising")).toHaveClass("bg-success");
  });

  testCase("shows a falling trend when the total is below its EMA", () => {
    render(
      <MarketBreadthCard
        {...defaultProps}
        cumulativeBreadth={[-40, 40, 10, -5, -25]}
      />,
    );

    expectValue(rtlScreen.getByText("Trend: falling")).toHaveClass("bg-danger");
  });

  testCase("shows the change of the total over the last hour", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    expectValue(rtlScreen.getByText("Last 1h: +85")).toBeInTheDocument();
  });

  testCase("hides the last hour change without a sample one hour ago", () => {
    render(
      <MarketBreadthCard
        {...defaultProps}
        cumulativeBreadth={[60, 40]}
        timestamps={timestamps.slice(0, 2)}
      />,
    );

    expectValue(rtlScreen.queryByText(/Last 1h/)).not.toBeInTheDocument();
  });

  testCase("shows unavailable when there is no cumulative breadth", () => {
    render(<MarketBreadthCard {...defaultProps} cumulativeBreadth={[null]} />);

    expectValue(rtlScreen.getByText("Trend: N/A")).toHaveClass("bg-secondary");
  });

  testCase("plots the cumulative breadth and its EMA as separate lines", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    const props = latestPlotlyProps();

    expectValue(props.data.map((trace) => trace.name)).toEqual([
      "Cumulative breadth",
      "EMA (4h)",
    ]);
    expectValue(props.data[0].line?.color).not.toEqual(
      props.data[1].line?.color,
    );
    expectValue(props.layout.yaxis?.range).toBeUndefined();
    expectValue(props.layout.yaxis2).toBeUndefined();
  });

  testCase("plots chart data oldest-to-newest", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    const [cumulativeTrace, emaTrace] = latestPlotlyProps().data;

    expectValue(cumulativeTrace.x).toEqual([...timestamps].reverse());
    expectValue(cumulativeTrace.y).toEqual([-25, -5, 10, 40, 60]);
    expectValue(emaTrace.y).toEqual([-8.0, -6.0, -2.3, 5.1, 12.4]);
  });

  testCase("waits for futures prices when no breadth is available", () => {
    render(
      <MarketBreadthCard
        {...defaultProps}
        cumulativeBreadth={[null]}
        cumulativeBreadthEma={[null]}
      />,
    );

    expectValue(
      rtlScreen.getByText("Waiting for futures price snapshots."),
    ).toBeInTheDocument();
    expectValue(plotlyChartMock).not.toHaveBeenCalled();
  });
});
