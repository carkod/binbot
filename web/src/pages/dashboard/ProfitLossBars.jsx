import React from "react";
import Plot from "react-plotly.js";
import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "reactstrap";

function BarChart({ data, width = "100%", height = "100%" }) {
  const layout = {
    autosize: false,
    margin: {
      r: 6,
      t: 2,
      b: 60,
      l: 35,
    },
    showlegend: false,
    width: width,
    height: height,
    xaxis: {
      autorange: true,
      title: "Date",
      type: "date",
      tickformat: "%d/%m",
    },
    yaxis: {
      type: "bar",
    },
  };

  return (
    <>
      <Plot data={data} layout={layout} useResizeHandler={true} />
    </>
  );
}

export function ProfitLossBars({ data }) {
  return (
    <Card className="card-chart">
      <CardHeader>
        <CardTitle tag="h5">Historical Profit &amp; Loss</CardTitle>
        <p className="card-category">Daily profit or loss in USD</p>
      </CardHeader>
      <CardBody>
        <BarChart data={data} width="300" height="200" />
      </CardBody>
      <CardFooter>
        <hr />
        <div className="card-stats">
          <i className="fa fa-check" /> Updated Daily
        </div>
      </CardFooter>
    </Card>
  );
}
