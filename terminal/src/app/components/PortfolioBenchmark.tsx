import { CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip as Tip, Title } from "chart.js";
import { type FC } from "react";
import { Card, Col, Container, Row } from "react-bootstrap";
import { Line } from "react-chartjs-2";
import { type BenchmarkSeriesData } from "../../features/balanceApiSlice";
import { listCssColors } from "../../utils/validations";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tip,
  Legend
);


const PortfolioBenchmarkChart: FC<{ chartData: BenchmarkSeriesData }> = ({
  chartData,
}) => {
  const lastUsdt = chartData.usdcSeries?.[chartData.usdcSeries.length - 1];
  const lastBtc = chartData.btcSeries?.[chartData.btcSeries.length - 1];

  const PBOptions = {
    maintainAspectRatio: true,
    responsive: true,
    scales: {
      y: {
        grace: "30%",
        ticks: {
          stepSize: 0.5,
        },
        grid: {
          display: true,
        },
      },
      x: {
        border: {
          display: true,
        },
        stacked: true,
        grid: {
          display: true,
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
    },
  };

  const data = {
    labels: chartData.datesSeries,
    datasets: [
      {
        label: "Portfolio in USDCSeries",
        data: chartData.usdcSeries,
        backgroundColor: listCssColors[0],
        borderColor: listCssColors[0],
      },
      {
        label: "BTC prices",
        data: chartData.btcSeries,
        backgroundColor: listCssColors[1],
        borderColor: listCssColors[1],
      },
    ],
  };

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
                <p className="u-text-left">
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
        <Line data={data} options={PBOptions}/>
      </Card.Body>
      <Card.Footer>
        {chartData.datesSeries && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {chartData.datesSeries[chartData.datesSeries.length - 1]}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default PortfolioBenchmarkChart;
