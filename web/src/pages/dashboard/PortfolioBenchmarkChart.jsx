import React from "react";
import Plot from "react-plotly.js";
import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "reactstrap";
import { listCssColors } from "../../validations";

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
    showlegend: true,
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
            marker: {color: listCssColors[7]},
            name: 'BTC prices',
          },
          {
            x: data.dates,
            y: data.usdt,
            type: 'scatter',
            mode: 'lines',
            marker: {color: listCssColors[4]},
            name: "USDT balance"
          }
        ]}
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
      {data && 
        <CardBody>
          <LineChart data={data} />
        </CardBody>
      }
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
