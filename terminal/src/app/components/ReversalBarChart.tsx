import { Row, Col, Container, Card } from "react-bootstrap"
import BarChart from "./BarChart"
import { type FC } from "react"

type ReversalBarChartProps = {
  data: any
  legend: any
}

const ReversalBarChart: FC<ReversalBarChartProps> = ({ data, legend }) => {
  const gainers = parseFloat(data.gainers_count)
  const losers = parseFloat(data.losers_count)
  return (
    <Card className="card-chart">
      <Card.Header>
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
              <Card.Title as="h5">Gainers vs. Losers by Volume</Card.Title>
              <p className="card-category u-text-left">
                Market evolution of gainers vs losers by volume.
              </p>
            </Col>
          </Row>
        </Container>
      </Card.Header>
      {data && (
        <Card.Body>
          <BarChart data={data} line1name="Gainers" line2name="Losers" />
        </Card.Body>
      )}
      <Card.Footer>
        <div className="legend">
          {legend &&
            legend.map((x, i) => {
              return (
                <span key={i} className="u-legend-text">
                  <i className="fa fa-circle" style={{ color: x.color }} />
                  {x.name}
                </span>
              )
            })}
        </div>
        <hr />
        {data.dates && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {data.dates[data.dates.length - 1]}
          </div>
        )}
      </Card.Footer>
    </Card>
  )
}

export default ReversalBarChart
