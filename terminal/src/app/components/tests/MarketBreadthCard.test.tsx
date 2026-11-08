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
      zeroline?: boolean;
    };
    yaxis2?: {
      title?: string;
    };
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
  marketBreadth: [0.12, 0.08, 0.03],
  marketBreadthMa: [0.171, 0.137, 0.1],
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

  testCase("shows a positive smoothed delta badge", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    expectValue(rtlScreen.getByText("+3.4 pts").className).toContain(
      "bg-success",
    );
  });

  testCase("shows a negative smoothed delta badge", () => {
    render(
      <MarketBreadthCard
        {...defaultProps}
        marketBreadthMa={[0.13, 0.171, 0.1]}
      />,
    );

    expectValue(rtlScreen.getByText("-4.1 pts").className).toContain(
      "bg-danger",
    );
  });

  testCase("shows a neutral badge for zero smoothed delta", () => {
    render(
      <MarketBreadthCard
        {...defaultProps}
        marketBreadthMa={[0.13, 0.13, 0.1]}
      />,
    );

    expectValue(rtlScreen.getByText("0.0 pts").className).toContain(
      "bg-secondary",
    );
  });

  testCase(
    "shows an unavailable badge when smoothed data is insufficient",
    () => {
      render(<MarketBreadthCard {...defaultProps} marketBreadthMa={[0.13]} />);

      expectValue(rtlScreen.getByText("N/A").className).toContain(
        "bg-secondary",
      );
    },
  );

  testCase(
    "shows recent falling shares and plots median returns on a percent axis",
    () => {
      render(<MarketBreadthCard {...defaultProps} />);

      const props = latestPlotlyProps();

      expectValue(props.data.map((trace) => trace.name)).toEqual([
        "Market Breadth",
        "Breadth Trend",
        "Median return (1h)",
        "Median return (3h)",
      ]);
      expectValue(props.layout.yaxis?.zeroline).toBe(true);
      expectValue(props.layout.yaxis2?.title).toBe("Median return (%)");
      expectValue(props.data[2].yaxis).toBe("y2");
      expectValue(props.data[3].yaxis).toBe("y2");
      expectValue(rtlScreen.getByText(/1h: 60% falling/)).toBeInTheDocument();
      expectValue(rtlScreen.getByText(/3h: 80% falling/)).toBeInTheDocument();
    },
  );

  testCase("plots chart data oldest-to-newest", () => {
    render(<MarketBreadthCard {...defaultProps} />);

    const props = latestPlotlyProps();
    const [
      marketBreadthTrace,
      breadthTrendTrace,
      oneHourTrace,
      threeHourTrace,
    ] = props.data;

    expectValue(marketBreadthTrace.x).toEqual([...timestamps].reverse());
    expectValue(marketBreadthTrace.y).toEqual([0.03, 0.08, 0.12]);
    expectValue(breadthTrendTrace.y).toEqual([0.1, 0.137, 0.171]);
    expectValue(oneHourTrace.y).toEqual([0.1, -0.4, -0.8]);
    expectValue(threeHourTrace.y).toEqual([-0.2, -1.2, -1.7]);
  });
});
