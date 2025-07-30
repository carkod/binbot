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
import React, { type FC } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { type BenchmarkSeriesData } from "../../features/balanceApiSlice";
import { listCssColors } from "../../utils/validations";
import { useBreakpoint } from "../hooks";
import { formatTimestamp } from "../../utils/time";
import Plot from "react-plotly.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tip,
  Legend,
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

  // Prepare Plotly data and layout for line plot
  const plotlyData = [
    {
      x: processData.datesSeries,
      y: processData.usdcSeries,
      type: "scatter",
      mode: "lines+markers",
      name: "Portfolio in USDCSeries",
      line: { color: listCssColors[0] },
    },
    {
      x: processData.datesSeries,
      y: processData.btcSeries,
      type: "scatter",
      mode: "lines+markers",
      name: "BTC prices",
      line: { color: listCssColors[1] },
    },
  ];

  const PBLayout = {
    title: false,
    autosize: true,
    margin: { t: 10, l: 40, r: 20, b: 40 },
    legend: { orientation: "h", x: 0, y: 1.1 },
    xaxis: {
      title: "Date",
      showgrid: true,
      type: "date",
      tickformat: "%Y-%m-%d", // Show as YYYY-MM-DD
      visible: true,
    },
    yaxis: {
      title: "% Difference",
      showgrid: true,
      zeroline: true,
      gridcolor: "#eee",
    },
    responsive: true,
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
            <Card.Title as="h5" className="mt-0">
              Portfolio benchmarking
            </Card.Title>
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
        <Plot
          data={plotlyData}
          layout={PBLayout}
          style={{ width: breakpoint === "xs" ? "100%" : "100%" }}
          useResizeHandler
        />
      </Card.Body>
      <Card.Footer>
        {chartData.datesSeries && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {formatTimestamp(
              chartData.datesSeries[chartData.datesSeries.length - 1],
            )}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default PortfolioBenchmarkChart;
