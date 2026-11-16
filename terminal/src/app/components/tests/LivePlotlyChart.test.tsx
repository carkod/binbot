import { vi } from "vitest";
import { render, screen as testingScreen } from "../../../utils/render";
import LivePlotlyChart from "../LivePlotlyChart";

const { plot } = vi.hoisted(() => ({ plot: vi.fn() }));

vi.mock("../PlotlyChart", () => ({
  default: (props: Record<string, unknown>) => {
    plot(props);
    return <div data-testid="live-chart" />;
  },
}));

describe("live chart updates", () => {
  it("transitions new observations in the mounted plot while keeping gaps and hover data", () => {
    const layout = { xaxis: { type: "date" }, height: 380 };

    const { rerender } = render(
      <LivePlotlyChart data={[{ x: ["first"], y: [100] }]} layout={layout} />,
    );

    const mountedChart = testingScreen.getByTestId("live-chart");

    const data = [
      {
        ids: ["first", "gap", "latest"],
        x: ["first", "gap", "latest"],
        y: [100, null, 140],
        customdata: [
          [100, 0],
          [null, null],
          [40, 0],
        ],
        connectgaps: false,
      },
    ];

    rerender(<LivePlotlyChart data={data} layout={layout} />);

    expect(testingScreen.getByTestId("live-chart")).toBe(mountedChart);

    const props = plot.mock.lastCall[0];

    expect(props.data).toBe(data);
    expect(props.layout).toMatchObject({
      ...layout,
      uirevision: "microstructure",
      transition: {
        duration: 300,
        easing: "cubic-out",
        ordering: "axes first",
      },
    });
  });

  it("skips Plotly updates when parent status changes leave chart inputs unchanged", () => {
    const data = [{ y: [100] }];

    const layout = { height: 380 };

    const { rerender } = render(
      <LivePlotlyChart data={data} layout={layout} />,
    );

    const calls = plot.mock.calls.length;

    rerender(<LivePlotlyChart data={data} layout={layout} />);
    expect(plot).toHaveBeenCalledTimes(calls);

    const nextLayout = { ...layout, xaxis: { range: [1, 2] } };

    rerender(<LivePlotlyChart data={data} layout={nextLayout} />);
    expect(plot.mock.lastCall[0].layout.xaxis.range).toEqual([1, 2]);
  });
});
