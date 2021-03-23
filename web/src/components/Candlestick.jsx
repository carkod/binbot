import React from "react";
import Plot from "react-plotly.js";
import { generateOrders } from "./services/candlestick.service";

function Candlestick({ data, bot }) {
  const { annotations, shapes } = generateOrders(data, bot);
  const layout = {
    dragmode: "zoom",
    autosize: true,
    line_width: 50,
    margin: {
      r: 10,
      t: 25,
      b: 35,
      l: 20,
    },
    showlegend: false,
    xaxis: {
      autorange: true,
      title: "Date",
      type: "date",
    },
    yaxis: {
      domain: [0, 1],
      tickformat: ".10f",
      type: "linear",
      maxPoints: 50,
    },
    annotations: annotations,
    shapes: shapes,
  };

  return (
    <Plot
      data={data.trace}
      layout={layout}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%" }}
    />
  );
}

export default Candlestick;
