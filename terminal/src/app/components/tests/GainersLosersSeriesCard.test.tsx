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
  text?: string[];
};

type PlotlyProps = {
  data: PlotlyTrace[];
  layout: {
    yaxis?: {
      zeroline?: boolean;
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

import GainersLosersSeriesCard from "../GainersLosersSeriesCard";

const snapshots = [
  {
    source: "kucoin_futures",
    recorded_at: "2026-08-10T10:00:00Z",
    top_gainers: [
      { symbol: "AUSDCM", price_change_percent: 12 },
      { symbol: "BUSDCM", price_change_percent: 8 },
    ],
    top_losers: [
      { symbol: "CUSDCM", price_change_percent: -4 },
      { symbol: "DUSDCM", price_change_percent: -6 },
    ],
  },
  {
    source: "kucoin_futures",
    recorded_at: "2026-08-10T09:00:00Z",
    top_gainers: [
      { symbol: "EUSDCM", price_change_percent: 5 },
      { symbol: "FUSDCM", price_change_percent: 3 },
    ],
    top_losers: [
      { symbol: "GUSDCM", price_change_percent: -8 },
      { symbol: "HUSDCM", price_change_percent: -10 },
    ],
  },
];

const latestPlotlyProps = () => {
  const call = plotlyChartMock.mock.calls.at(-1);
  expectValue(call).toBeDefined();

  return call?.[0] as PlotlyProps;
};

describeBlock("GainersLosersSeriesCard", () => {
  beforeEachTest(() => {
    plotlyChartMock.mockClear();
  });

  testCase("plots average top-mover changes oldest-to-newest", () => {
    render(<GainersLosersSeriesCard snapshots={snapshots} />);

    const props = latestPlotlyProps();
    const [gainersTrace, losersTrace] = props.data;

    expectValue(props.data.map((trace) => trace.name)).toEqual([
      "Top gainers average",
      "Top losers average",
    ]);
    expectValue(gainersTrace.x).toEqual([
      "2026-08-10T09:00:00Z",
      "2026-08-10T10:00:00Z",
    ]);
    expectValue(gainersTrace.y).toEqual([4, 10]);
    expectValue(losersTrace.y).toEqual([-9, -5]);
    expectValue(props.layout.yaxis?.zeroline).toBe(true);
  });

  testCase("shows snapshot symbols in the hover data", () => {
    render(<GainersLosersSeriesCard snapshots={snapshots} />);

    const [gainersTrace, losersTrace] = latestPlotlyProps().data;

    expectValue(gainersTrace.text?.[1]).toContain("AUSDCM: +12%");
    expectValue(losersTrace.text?.[1]).toContain("CUSDCM: -4%");
  });

  testCase("shows the latest net momentum badge", () => {
    render(<GainersLosersSeriesCard snapshots={snapshots} />);

    expectValue(rtlScreen.getByText("+5.0 pts net").className).toContain(
      "bg-success",
    );
  });
});
