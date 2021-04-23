import React from "react";
import Plot from "react-plotly.js";
import { Button, Card, CardBody, CardHeader, CardTitle } from "reactstrap";

function LineChart({ data, width, height }) {
  const layout = {
    dragmode: "zoom",
    autosize: false,
    line_width: 50,
    margin: {
      r: 6,
      t: 2,
      b: 60,
      l: 35,
    },
    showlegend: false,
    height: height,
    width: width,
    xaxis: {
      autorange: true,
      title: "Date",
      type: "date",
      tickformat: "%d/%m",
    },
    yaxis: {
      type: "linear",
      maxPoints: 50,
    },
  };

  return (
    <>
      <Plot data={data} layout={layout} useResizeHandler={true} />
    </>
  );
}

export function NetWorthChart({ data }) {
  return (
    <Card className="card-chart">
      <CardHeader>
        <CardTitle tag="h5">Net Worth</CardTitle>
        <p className="card-category">Estimated Portfolio Value in USD</p>
        <Button className="u-title-btn" type="button">
          7 days
        </Button>
      </CardHeader>
      <CardBody>
        <LineChart data={data} width="300" height="200" />
      </CardBody>
    </Card>
  );
}
