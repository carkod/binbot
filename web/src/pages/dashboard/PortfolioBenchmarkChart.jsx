import React from "react";
import DashboardLineChart from "../../components/DashboardLineChart";
import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "reactstrap";
import { Row, Col, Container } from "react-bootstrap";

export function PortfolioBenchmarkChart({ data, legend }) {
  const lastUsdt = data.usdc ? data.usdc[data.usdc.length - 1] : data.usdt[data.usdt.length - 1];
  const lastBtc = data.btc[data.btc.length - 1];
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
          <DashboardLineChart data={data} />
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
            <i className="fa fa-check" /> Last updated {data.dates[data.dates.length - 1]}
          </div>
        }
      </CardFooter>
    </Card>
  );
}

