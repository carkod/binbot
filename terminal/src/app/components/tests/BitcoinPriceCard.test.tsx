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
      title?: { text?: string; standoff?: number };
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

const latestPlotlyProps = () => {
  const call = plotlyChartMock.mock.calls.at(-1);
  expectValue(call).toBeDefined();

  return call?.[0] as PlotlyProps;
};

describeBlock("BitcoinPriceCard", () => {
  beforeEachTest(() => {
    plotlyChartMock.mockClear();
  });

  testCase("plots BTC close prices on their candle timestamps", () => {
    render(<BitcoinPriceCard btcCloseSeries={btcCloseSeries} />);

    const props = latestPlotlyProps();

    expectValue(props.data).toHaveLength(1);
    expectValue(props.data[0].name).toBe("BTC close");
    expectValue(props.data[0].x).toEqual(btcCloseSeries.timestamp);
    expectValue(props.data[0].y).toEqual([64800, 65000, 65125.5]);
    expectValue(props.layout.yaxis?.title).toEqual({
      text: "Close price",
      standoff: 14,
    });
  });

  testCase("shows the latest close price", () => {
    render(<BitcoinPriceCard btcCloseSeries={btcCloseSeries} />);

    expectValue(rtlScreen.getByText("65,125.5")).toBeInTheDocument();
  });
});
