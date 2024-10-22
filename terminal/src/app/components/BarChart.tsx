import Plot from "react-plotly.js";
import { listCssColors } from "../../utils/validations";
import { type FC } from "react";

interface BarChartProps {
  data: any;
  width?: string;
  height?: string;
  line1name?: string;
  line2name?: string;
}

const BarChart: FC<BarChartProps> = ({
  data,
  width = "100%",
  height = "100%",
  line1name = "BTC prices",
  line2name = "USDC balance",
}) => {
  const layout = {
    dragmode: "zoom",
    autosize: true,
    line_width: 50,
    barmode: "stack",
    margin: {
      r: 6,
      t: 35,
      b: 15,
      l: 35,
    },
    showlegend: true,
    legend: {
      x: 0,
      xanchor: "left",
      y: 15,
    },
    xaxis: {
      autorange: true,
      type: "date",
    },
    yaxis: {
      type: "linear",
      maxPoints: 50,
    },
  };

  return (
    <>
      <Plot
        data={[
          {
            x: data.dates,
            y: data.gainers_percent,
            type: "bar",
            marker: { color: listCssColors[8] },
            name: line1name,
            text: data.gainers,
          },
          {
            x: data.dates,
            y: data.losers_percent,
            type: "bar",
            marker: { color: listCssColors[2] },
            name: line2name,
            text: data.losers,
          },
        ]}
        layout={layout}
        useResizeHandler={true}
        style={{ width: width, height: height }}
      />
    </>
  );
};

export default BarChart;
