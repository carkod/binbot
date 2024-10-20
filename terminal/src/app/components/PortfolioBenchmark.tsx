import { type ChartOptions } from "chart.js"
import "chart.js/auto" // Fixes rendering issues with chart.js
import { Card, Col, Container, Row } from "react-bootstrap"
import { Line } from "react-chartjs-2"
import { listCssColors } from "../../utils/validations"

const PortfolioBenchmarkChart = ({ chartData }) => {
  const lastUsdt = chartData.usdcSeries?.[chartData.usdcSeries.length - 1]
  const lastBtc = chartData.btcSeries?.[chartData.btcSeries.length - 1]

  const PBOptions: ChartOptions = {
    maintainAspectRatio: true,
    scales: {
      y: {
        type: "linear",
        grace: "30%",
        ticks: {
          stepSize: 0.5,
        },
        grid: {
          display: false,
        },
      },
      x: {
        border: {
          display: true,
        },
        stacked: true,
        grid: {
          display: false,
        },
      },
    },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: "rgb(255, 99, 132)",
        },
      },
      tooltip: {
        enabled: true,
        intersect: true,
        mode: "index",
        position: "nearest",
      },
    },
  }

  const data = {
    labels: chartData.datesSeries,
    datasets: [
      {
        type: "line",
        label: "Portfolio in USDCSeries",
        data: chartData.usdcSeries,
        borderColor: listCssColors[0],
      },
      {
        type: "line",
        label: "BTC prices",
        data: chartData.btcSeries,
        borderColor: listCssColors[1],
      },
    ],
  }

  return (
    <Card className="card-chart">
      <Card.Header>
        <Container>
          <Row>
            <Col lg="1" md="1" sm="1">
              <div className="u-fa-lg">
                <i
                  className={`fa fa-suitcase ${lastUsdt > lastBtc ? "text-success" : lastUsdt < lastBtc ? "text-danger" : ""}`}
                />
              </div>
            </Col>
            <Col lg="11" md="11" sm="11">
              <Card.Title as="h5">Portfolio benchmarking</Card.Title>
              <div>
                <p className="card-category u-text-left">
                  Compare portfolio against BTC.
                  <br />
                  Values in % difference
                </p>
              </div>
            </Col>
          </Row>
        </Container>
      </Card.Header>
      <Card.Body>
        <Line data={data} options={PBOptions} />
      </Card.Body>
      <Card.Footer>
        {/* <div className="legend">
          {legend &&
            legend.map((x, i) => {
              return (
                <span key={i} className="u-legend-text">
                  <i className="fa fa-circle" style={{ color: x.color }} />
                  {x.name}
                </span>
              )
            })}
        </div> */}
        <hr />
        {chartData.dates && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {chartData.dates[chartData.dates.length - 1]}
          </div>
        )}
      </Card.Footer>
    </Card>
  )
}

export default PortfolioBenchmarkChart
