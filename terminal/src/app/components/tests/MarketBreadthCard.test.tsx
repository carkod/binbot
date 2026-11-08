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
};

type PlotlyProps = {
  data: PlotlyTrace[];
  layout: {
    yaxis?: {
      title?: { text?: string; standoff?: number };
      zeroline?: boolean;
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
];

const defaultProps = {
  medianReturn15m: [-0.3, -0.1, 0.2],
  medianReturn1h: [-0.8, -0.4, 0.1],
  medianReturn3h: [-1.7, -1.2, -0.2],
  fallingShare1h: [0.6, 0.5, 0.3],
  fallingShare3h: [0.8, 0.7, 0.6],
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

  testCase("uses the latest 15-minute median return for the badge", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    expectValue(rtlScreen.getByText("15m: -0.30%")).toHaveClass("bg-danger");
  });

  testCase("shows a positive 15-minute median return", () => {
    render(<MarketBreadthCard {...defaultProps} medianReturn15m={[0.4567]} />);

    expectValue(rtlScreen.getByText("15m: +0.46%")).toHaveClass("bg-success");
  });

  testCase("shows unavailable when no 15-minute comparison exists", () => {
    render(<MarketBreadthCard {...defaultProps} medianReturn15m={[null]} />);

    expectValue(rtlScreen.getByText("15m: N/A")).toHaveClass("bg-secondary");
  });

  testCase("plots only recent median returns on one percentage axis", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    const props = latestPlotlyProps();

    expectValue(props.data.map((trace) => trace.name)).toEqual([
      "Median return (15m)",
      "Median return (1h)",
      "Median return (3h)",
    ]);
    expectValue(props.layout.yaxis?.zeroline).toBe(true);
    expectValue(props.layout.yaxis?.title).toEqual({
      text: "Median return (%)",
      standoff: 14,
    });
    expectValue(props.layout.yaxis2).toBeUndefined();
    expectValue(props.data.every((trace) => trace.yaxis === undefined)).toBe(
      true,
    );
    expectValue(rtlScreen.getByText(/1h: 60% falling/)).toBeInTheDocument();
    expectValue(rtlScreen.getByText(/3h: 80% falling/)).toBeInTheDocument();
  });

  testCase("plots chart data oldest-to-newest", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    const props = latestPlotlyProps();
    const [fifteenMinuteTrace, oneHourTrace, threeHourTrace] = props.data;

    expectValue(fifteenMinuteTrace.x).toEqual([...timestamps].reverse());
    expectValue(fifteenMinuteTrace.y).toEqual([0.2, -0.1, -0.3]);
    expectValue(oneHourTrace.y).toEqual([0.1, -0.4, -0.8]);
    expectValue(threeHourTrace.y).toEqual([-0.2, -1.2, -1.7]);
  });

  testCase(
    "waits for futures prices when no return window is available",
    () => {
      render(
        <MarketBreadthCard
          {...defaultProps}
          medianReturn15m={[null]}
          medianReturn1h={[null]}
          medianReturn3h={[null]}
        />,
      );

      expectValue(
        rtlScreen.getByText("Waiting for futures price snapshots."),
      ).toBeInTheDocument();
      expectValue(plotlyChartMock).not.toHaveBeenCalled();
    },
  );
});
