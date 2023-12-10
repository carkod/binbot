import Plot from "react-plotly.js";
import { listCssColors } from "../validations";

export default function BarChart({ data, width = "100%", height = "100%", line1name='BTC prices', line2name="USDT balance"}) {

  const layout = {
    dragmode: "zoom",
    autosize: true,
    line_width: 50,
    barmode: 'stack',
    margin: {
      r: 6,
      t: 35,
      b: 15,
      l: 35,
    },
    showlegend: true,
    legend: {
      x: 0,
      xanchor: 'left',
      y: 1
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

  const dataTotal = `${data.gainers_count + data.losers_count}`;
  const gainersCount = `${((data.gainers_count / dataTotal) * 100).toFixed(2)}%`;
  const losersCount = `${((data.losers_count / dataTotal) * 100).toFixed(2)}%`;

  return (
    <>
      <Plot
        data={[
          {
            x: data.dates,
            y: data.gainers_percent,
            type: 'bar',
            marker: {color: listCssColors[8]},
            name: line1name,
            text: gainersCount,
          },
          {
            x: data.dates,
            y: data.losers_percent,
            type: 'bar',
            marker: {color: listCssColors[2]},
            name: line2name,
            text: losersCount,
          }
        ]}
        layout={layout}
        useResizeHandler={true}
        style={{ width: width, height: height }}
      />
    </>
  );
}
  