import React from "react";
import Plot from "react-plotly.js";
import { listCssColors } from "../../utils/validations";
import { type FC } from "react";
import { type GainerLosersData } from "../../features/marketApiSlice";

interface BarChartProps {
  data: GainerLosersData;
  width?: string;
  height?: string;
  line1name?: string;
  line2name?: string;
}

const BarChart: FC<BarChartProps> = ({
  data,
  width = "100%",
  height = "100%",
}) => {
  // Parse percentages from string values like "33.89%"
  const gainers_percent = data.gainers.map((v: string) =>
    typeof v === "string" ? parseFloat(v.replace("%", "")) : v
  );
  const losers_percent = data.losers.map((v: string) =>
    typeof v === "string" ? parseFloat(v.replace("%", "")) : v
  );

  const reversalIndices: number[] = [];
  for (let i = 1; i < gainers_percent.length; i++) {
    const prevDiff = gainers_percent[i - 1] - losers_percent[i - 1];
    const currDiff = gainers_percent[i] - losers_percent[i];
    if ((prevDiff <= 0 && currDiff > 0) || (prevDiff >= 0 && currDiff < 0)) {
      reversalIndices.push(i);
    }
  }

  // Prepare vertical line shapes for reversals
  const reversalShapes = reversalIndices.map((i) => ({
    type: "line",
    x0: data.dates[i],
    x1: data.dates[i],
    y0: 0,
    y1: 100,
    xref: "x",
    yref: "y",
    line: {
      color: "blue",
      width: 2,
      dash: "dash",
    },
  }));

  const layout = {
    dragmode: "zoom",
    autosize: true,
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
      y: 1,
    },
    xaxis: {
      autorange: true,
      type: "date",
      title: { text: "Date", font: { size: 16, family: "Arial" } },
    },
    yaxis: {
      type: "linear",
      title: { text: "Percent (%)", font: { size: 16, family: "Arial" } },
      range: [0, 100],
    },
    shapes: reversalShapes,
  };

  return (
    <Plot
      data={[
        {
          x: data.dates,
          y: gainers_percent,
          type: "scatter",
          mode: "lines",
          fill: "tozeroy",
          fillcolor: listCssColors[8],
          line: { color: listCssColors[8] },
          name: "gainers_percent",
        } as any,
        {
          x: data.dates,
          y: losers_percent,
          type: "scatter",
          mode: "lines",
          fill: "tonexty",
          fillcolor: listCssColors[2],
          line: { color: listCssColors[2] },
          name: "losers_percent",
        } as any,
      ]}
      layout={layout}
      useResizeHandler={true}
      style={{ width: width, height: height }}
    />
  );
};

export default BarChart;
