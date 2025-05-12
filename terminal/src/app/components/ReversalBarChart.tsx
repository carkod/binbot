import React, { type FC } from "react";
import { Card, Col, Row } from "react-bootstrap";
import { type GainerLosersData } from "../../features/marketApiSlice";
import { useBreakpoint } from "../hooks";
import BarChart from "./BarChart";
import moment from "moment";

type ReversalBarChartProps = {
  chartData: GainerLosersData;
  legend: any;
};

const ReversalBarChart: FC<ReversalBarChartProps> = ({ chartData, legend }) => {
  const breakpoint = useBreakpoint();
  const data = { ...chartData };

  if (breakpoint === "xs") {
    // Show only the last 5 data points due to size of the screen
    data.gainers_count = chartData.gainers_count?.slice(-10);
    data.losers_count = chartData.losers_count?.slice(-10);
    data.dates = chartData.dates?.slice(-10);
    data.gainers_percent = chartData.gainers_percent?.slice(-10);
    data.losers_percent = chartData.losers_percent?.slice(-10);
    data.gainers = chartData.gainers?.slice(-10);
    data.losers = chartData.losers?.slice(-10);
    data.total_volume = chartData.total_volume?.slice(-10);
  }

  const gainers = data.gainers_count;
  const losers = data.losers_count;

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i
              className={`fs-2 fa fa-suitcase ${
                gainers > losers
                  ? "text-success"
                  : gainers < losers
                    ? "text-danger"
                    : ""
              }`}
            />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title as="h5" className="mt-0">
              Gainers vs. Losers by Volume
            </Card.Title>
            <p className="u-text-left">
              Market evolution of gainers vs losers by volume. This graph shows
              indications of market reversal
            </p>
          </Col>
        </Row>
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
              );
            })}
        </div>
        <hr />
        {data.dates && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {moment(data.dates[0]).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default ReversalBarChart;
