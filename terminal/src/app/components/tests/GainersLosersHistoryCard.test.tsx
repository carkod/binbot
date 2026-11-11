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
    customdata?: Array<Array<number>>;
    hovertemplate?: string;
  }>;
  layout: {
    yaxis?: {
      title?: { text?: string };
      range?: number[];
      zeroline?: boolean;
    };
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

  testCase("shows one signed balance line for gain and loss magnitude", () => {
    render(<GainersLosersHistoryCard points={points} />);

    expectValue(rtlScreen.getByText("Balance +50.0%")).toBeInTheDocument();
    expectValue(plotlyChartMock).toHaveBeenCalledTimes(1);
    const chart = plotlyChartMock.mock.calls[0][0] as PlotlyProps;
    expectValue(chart.data.map((trace) => trace.name)).toEqual([
      "Gain/loss balance",
    ]);
    expectValue(chart.data[0].x).toEqual([
      "2026-11-10T10:00:00Z",
      "2026-11-10T11:00:00Z",
    ]);
    expectValue(chart.data[0].y).toEqual([-50, 50]);
    expectValue(chart.data[0].customdata).toEqual([
      [25, 75, 25, 15],
      [75, 25, 30, 10],
    ]);
    expectValue(chart.data[0].hovertemplate).toContain("Balance %{y:+.1f}%");
    expectValue(chart.layout.yaxis?.title?.text).toBe("Gain/loss balance (%)");
    expectValue(chart.layout.yaxis?.range).toEqual([-100, 100]);
    expectValue(chart.layout.yaxis?.zeroline).toBe(true);
    expectValue(chart.layout.yaxis2).toBeUndefined();
  });

  testCase("shows a placeholder without ranked moves", () => {
    render(<GainersLosersHistoryCard points={[]} />);

    expectValue(
      rtlScreen.getByText("Waiting for hourly futures price snapshots."),
    ).toBeInTheDocument();
    expectValue(plotlyChartMock).not.toHaveBeenCalled();
  });

  testCase("shows a placeholder when both sides have zero magnitude", () => {
    render(
      <GainersLosersHistoryCard
        points={[
          {
            timestamp: "2026-11-10T11:00:00Z",
            gainer_magnitude: 0,
            loser_magnitude: 0,
            advancers: 0,
            decliners: 0,
          },
        ]}
      />,
    );

    expectValue(
      rtlScreen.getByText("Waiting for hourly futures price snapshots."),
    ).toBeInTheDocument();
    expectValue(plotlyChartMock).not.toHaveBeenCalled();
  });
});
