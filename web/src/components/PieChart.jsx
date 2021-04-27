import React from "react";
import Plot from "react-plotly.js";

function PieChart({ data }) {
  const layout = {
    autosize: true,
    margin: {
      r: -5,
      t: -15,
      b: 10,
      l: 10,
    },
    height: 300,
    width: 300,
    showlegend: false,
  };

  return (
    <>
      <Plot
        data={data}
        layout={layout}
        style={{ width: "100%", height: "100%" }}
      />
    </>
  );
}

export default PieChart;
