import React from "react";
import Plot from "react-plotly.js";
import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "reactstrap";

function PieChart({ data }) {
  const layout = {
    autosize: true,
    margin: {
      r: 0,
      t: 0,
      b: 10,
      l: 20,
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

export function AssetsPie({ data, legend }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle tag="h5">Assets</CardTitle>
        <p className="card-category">
          Proportion of cryptoassets over estimated BTC value
        </p>
      </CardHeader>
      <CardBody>{data && <PieChart data={data} />}</CardBody>
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
      </CardFooter>
    </Card>
  );
}
