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
};

type PlotlyProps = {
  data: PlotlyTrace[];
  layout: {
    yaxis?: {
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

import BitcoinPriceCard from "../BitcoinPriceCard";

const btcCloseSeries = {
  symbol: "XBTUSDTM" as const,
  interval: "15m" as const,
  timestamp: [
    "2026-08-10T09:45:00Z",
    "2026-08-10T10:00:00Z",
    "2026-08-10T10:15:00Z",
  ],
  close: [64800, 65000, 65125.5],
};

const marketBreadthTimestamps = [
  "2026-08-10T10:15:04Z",
  "2026-08-10T10:00:03Z",
  "2026-08-10T09:45:02Z",
];

const latestPlotlyProps = () => {
  const call = plotlyChartMock.mock.calls.at(-1);
  expectValue(call).toBeDefined();

  return call?.[0] as PlotlyProps;
};

describeBlock("BitcoinPriceCard", () => {
  beforeEachTest(() => {
    plotlyChartMock.mockClear();
  });

  testCase("plots only BTC close prices on market-breadth timestamps", () => {
    render(
      <BitcoinPriceCard
        btcCloseSeries={btcCloseSeries}
        marketBreadthTimestamps={marketBreadthTimestamps}
      />,
    );

    const props = latestPlotlyProps();

    expectValue(props.data).toHaveLength(1);
    expectValue(props.data[0].name).toBe("BTC close");
    expectValue(props.data[0].x).toEqual([
      "2026-08-10T09:45:02Z",
      "2026-08-10T10:00:03Z",
      "2026-08-10T10:15:04Z",
    ]);
    expectValue(props.data[0].y).toEqual([64800, 65000, 65125.5]);
    expectValue(props.layout.yaxis?.title).toBe("Close price");
  });

  testCase(
    "leaves a gap when a breadth timestamp has no matching candle",
    () => {
      render(
        <BitcoinPriceCard
          btcCloseSeries={{
            ...btcCloseSeries,
            timestamp: btcCloseSeries.timestamp.slice(1),
            close: btcCloseSeries.close.slice(1),
          }}
          marketBreadthTimestamps={marketBreadthTimestamps}
        />,
      );

      expectValue(latestPlotlyProps().data[0].y).toEqual([
        null,
        65000,
        65125.5,
      ]);
    },
  );

  testCase("shows the latest close price", () => {
    render(
      <BitcoinPriceCard
        btcCloseSeries={btcCloseSeries}
        marketBreadthTimestamps={marketBreadthTimestamps}
      />,
    );

    expectValue(rtlScreen.getByText("65,125.5")).toBeInTheDocument();
  });
});
