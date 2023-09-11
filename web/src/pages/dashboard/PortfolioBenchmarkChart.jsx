import React from "react";
import Plot from "react-plotly.js";
import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "reactstrap";
import { Row, Col, Container } from "react-bootstrap";
import { listCssColors } from "../../validations";

function LineChart({ data, width = "100%", height = "100%" }) {
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
  const lastUsdt = data.usdt[0];
  const lastBtc = data.btc[0];
  return (
    <Card className="card-chart">
      <CardHeader>
        <Container>
          <Row>
          <Col lg="1" md="1" sm="1">
            <div className="u-fa-lg">
              <i className={`fa fa-suitcase ${lastUsdt > lastBtc ? "text-success": lastUsdt < lastBtc ? "text-danger" : ""}`} />
            </div>
          </Col>
          <Col lg="11" md="11" sm="11">
            <CardTitle tag="h5">
              Portfolio benchmarking
            </CardTitle>
            <p className="card-category u-text-left">Compare portfolio against BTC.Values in % difference</p>
          </Col>
          </Row>
        </Container>
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
        {data.dates &&
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated {data.dates[0]}
          </div>
        }
      </CardFooter>
    </Card>
  );
}
