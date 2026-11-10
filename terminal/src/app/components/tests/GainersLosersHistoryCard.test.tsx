import "@testing-library/jest-dom";
import { render, screen as rtlScreen } from "@testing-library/react";
import {
  beforeEach as beforeEachTest,
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
  vi,
} from "vitest";
import type { GainersLosersAggregatePoint } from "../../../features/marketApiSlice";

type PlotlyProps = {
  data: Array<{
    name?: string;
    x?: string[];
    y?: Array<number | null>;
    stackgroup?: string;
    customdata?: Array<Array<number>>;
  }>;
  layout: {
    yaxis?: { title?: { text?: string }; range?: number[] };
    yaxis2?: unknown;
  };
};

const plotlyChartMock = vi.hoisted(() =>
  vi.fn((props: PlotlyProps) => <div data-testid="plotly-chart" />),
);

vi.mock("../PlotlyChart", () => ({ default: plotlyChartMock }));

import GainersLosersHistoryCard from "../GainersLosersHistoryCard";

const points: GainersLosersAggregatePoint[] = [
  {
    timestamp: "2026-11-10T11:00:00Z",
    gainer_magnitude: 30,
    loser_magnitude: 10,
    advancers: 30,
    decliners: 10,
  },
  {
    timestamp: "2026-11-10T10:00:00Z",
    gainer_magnitude: 5,
    loser_magnitude: 15,
    advancers: 25,
    decliners: 15,
  },
];

describeBlock("GainersLosersHistoryCard", () => {
  beforeEachTest(() => plotlyChartMock.mockClear());

  testCase(
    "shows the hourly gain/loss magnitude share and preserves the absolute scale",
    () => {
      render(<GainersLosersHistoryCard points={points} />);

      expectValue(rtlScreen.getByText("Gainers 75.0%")).toBeInTheDocument();
      expectValue(plotlyChartMock).toHaveBeenCalledTimes(1);
      const chart = plotlyChartMock.mock.calls[0][0] as PlotlyProps;
      expectValue(chart.data.map((trace) => trace.name)).toEqual([
        "Gainers",
        "Losers",
      ]);
      expectValue(chart.data[0].x).toEqual([
        "2026-11-10T10:00:00Z",
        "2026-11-10T11:00:00Z",
      ]);
      expectValue(chart.data[0].y).toEqual([5, 30]);
      expectValue(chart.data[1].y).toEqual([15, 10]);
      expectValue(chart.data[0].stackgroup).toBe("one");
      expectValue(chart.data[1].stackgroup).toBe("one");
      expectValue(chart.data[0].customdata).toEqual([
        [25, 75, 20, 25, 15],
        [75, 25, 40, 30, 10],
      ]);
      expectValue(chart.layout.yaxis?.title?.text).toBe(
        "Combined 24h magnitude (pts)",
      );
      expectValue(chart.layout.yaxis?.range).toBeUndefined();
      expectValue(chart.layout.yaxis2).toBeUndefined();
    },
  );

  testCase("shows a placeholder without ranked moves", () => {
    render(<GainersLosersHistoryCard points={[]} />);

    expectValue(
      rtlScreen.getByText("Waiting for hourly futures price snapshots."),
    ).toBeInTheDocument();
    expectValue(plotlyChartMock).not.toHaveBeenCalled();
  });
});
