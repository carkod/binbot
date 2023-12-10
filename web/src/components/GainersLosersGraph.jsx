import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "reactstrap";
import { Row, Col, Container } from "react-bootstrap";
import BarChart from "./BarChart";


export default function GainersLosersGraph({ data, legend }) {
  const gainers = parseFloat(data.gainers_percent[data.gainers_percent.length - 1]);
  const losers = parseFloat(data.losers_percent[data.losers_percent.length - 1]);
  return (
    <Card className="card-chart">
      <CardHeader>
        <Container>
          <Row>
            <Col lg="1" md="1" sm="1">
              <div className="u-fa-lg">
                <i
                  className={`fa fa-suitcase ${
                    gainers > losers
                      ? "text-success"
                      : gainers < losers
                      ? "text-danger"
                      : ""
                  }`}
                />
              </div>
            </Col>
            <Col lg="11" md="11" sm="11">
              <CardTitle tag="h5">Gainers vs. Losers</CardTitle>
              <p className="card-category u-text-left">
                Market evolution of gainers vs losers.
              </p>
            </Col>
          </Row>
        </Container>
      </CardHeader>
      {data && (
        <CardBody>
          <BarChart data={data} line1name="Gainers" line2name="Losers" />
        </CardBody>
      )}
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
        {data.dates && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated {data.dates[data.dates.length - 1]}
          </div>
        )}
      </CardFooter>
    </Card>
  );
}
