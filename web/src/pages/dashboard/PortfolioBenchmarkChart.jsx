import React from "react";
import Plot from "react-plotly.js";
import {
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  CardTitle,
  Button,
} from "reactstrap";

function LineChart({ data, width = "100%", height = "100%" }) {
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
      <Plot
        data={data}
        layout={layout}
        useResizeHandler={true}
        style={{ width: width, height: height }}
      />
    </>
  );
}

export function PortfolioBenchmarkChart({ data, legend }) {
  return (
    <Card className="card-chart">
      <CardHeader>
        <CardTitle tag="h5">Portfolio benchmarking</CardTitle>
        <p className="card-category">Compare Portfolio against BTC and USDT</p>
      </CardHeader>
      <CardBody>{data && <LineChart data={data} />}</CardBody>
      <CardFooter>
        <div className="legend">
          {legend &&
            legend.map((x, i) => {
              return (
                <span key={i} className="u-legend-text">
                  <i className="fa fa-circle" style={{ color: x.color }} />
                  {x.name}
                </span>
              );
            })}
        </div>
        <hr />
        <div className="card-stats">
          <i className="fa fa-check" /> Updated everyday at 00:01
        </div>
      </CardFooter>
    </Card>
  );
}
