import React from "react";
import Plot from "react-plotly.js";

function LineChart({ data, width = "100%", height = "100%" }) {
  const layout = {
    dragmode: "zoom",
    autosize: true,
    line_width: 50,
    margin: {
      r: 10,
      t: 10,
      b: 35,
      l: 20,
    },
    showlegend: false,
    xaxis: {
      autorange: true,
      title: "Date",
      type: "date",
      tickformat: "%d/%m",
    },
    yaxis: {
      // domain: [0, 1],
      // tickformat: '.10f',
      type: "linear",
      maxPoints: 50,
    },
  };

  return (
    <>
      <Plot
        data={data}
        layout={layout}
        useResizeHandler={true}
        style={{ width: width, height: height }}
      />
    </>
  );
}

export default LineChart;
