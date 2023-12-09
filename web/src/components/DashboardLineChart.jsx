import Plot from "react-plotly.js";
import { listCssColors } from "../validations";

export default function DashboardLineChart({ data, width = "100%", height = "100%", line1name='BTC prices', line2name="USDT balance", }) {
    const layout = {
      dragmode: "zoom",
      autosize: true,
      line_width: 50,
      margin: {
        r: 6,
        t: 2,
        b: 35,
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
  
    return (
      <>
        <Plot
          data={[
            {
              x: data.dates,
              y: data.btc,
              type: 'scatter',
              mode: 'lines',
              marker: {color: "#F2A900"},
              name: line1name,
            },
            {
              x: data.dates,
              y: data.usdt,
              type: 'scatter',
              mode: 'lines',
              marker: {color: listCssColors[4]},
              name: line2name
            }
          ]}
          layout={layout}
          useResizeHandler={true}
          style={{ width: width, height: height }}
        />
      </>
    );
  }
  