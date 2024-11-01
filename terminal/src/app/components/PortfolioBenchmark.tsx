import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip as Tip,
  Title,
} from "chart.js";
import { useEffect, type FC } from "react";
import { Card, Col, Container, Row } from "react-bootstrap";
import { Line } from "react-chartjs-2";
import { type BenchmarkSeriesData } from "../../features/balanceApiSlice";
import { listCssColors } from "../../utils/validations";
import { useBreakpoint } from "../hooks";

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
  const breakpoint = useBreakpoint();
  let processData = { ...chartData };

  if (breakpoint === "xs") {
    // Show only the last 5 data points due to size of the screen
    processData.datesSeries = chartData.datesSeries?.slice(-5);
    processData.usdcSeries = chartData.usdcSeries?.slice(-5);
    processData.btcSeries = chartData.btcSeries?.slice(-5);
  }

  const lastUsdt = processData.usdcSeries?.[processData.usdcSeries.length - 1];
  const lastBtc = processData.btcSeries?.[processData.btcSeries.length - 1];

  const PBOptions = {
    maintainAspectRatio: true,
    responsive: true,
    scales: {
      y: {
        grace: "30%",
        ticks: {
          stepSize: 0.1,
        },
        grid: {
          display: true,
        },
      },
      x: {
        ticks: {
          display: false,
        },
        stacked: true,
        grid: {
          display: true,
        },
      },
    },
    plugins: {
      legend: {
        labels: {
          display: breakpoint !== "xs",
          color: "rgb(255, 99, 132)",
        },
      },
    },
  };

  const data = {
    labels: processData.datesSeries,
    datasets: [
      {
        label: "Portfolio in USDCSeries",
        data: processData.usdcSeries,
        backgroundColor: listCssColors[0],
        borderColor: listCssColors[0],
      },
      {
        label: "BTC prices",
        data: processData.btcSeries,
        backgroundColor: listCssColors[1],
        borderColor: listCssColors[1],
      },
    ],
  };

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i
              className={`fs-2 fa fa-suitcase ${lastUsdt > lastBtc ? "text-success" : lastUsdt < lastBtc ? "text-danger" : ""}`}
            />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title as="h5" className="mt-0">Portfolio benchmarking</Card.Title>
            <div>
              <p className="u-text-left">
                Compare portfolio against BTC.
                <br />
                Values in % difference
              </p>
            </div>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body className="px-0 w-10">
        <Line
          data={data}
          options={PBOptions}
          width={breakpoint === "xs" && "100%"}
        />
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
