import React from "react";
import { Badge, Card, Row, Col } from "react-bootstrap";
import moment from "moment";
import PlotlyChart from "./PlotlyChart";

type MarketBreadthCardProps = {
  marketBreadth: number[];
  marketBreadthMa?: Array<number | null>;
  strengthIndex?: number[];
  timestamps: string[];
};

const resolveDeltaBadge = (marketBreadthMa?: Array<number | null>) => {
  const latest = marketBreadthMa?.[0];
  const previous = marketBreadthMa?.[1];

  if (
    typeof latest !== "number" ||
    typeof previous !== "number" ||
    !Number.isFinite(latest) ||
    !Number.isFinite(previous)
  ) {
    return { bg: "secondary", label: "N/A" };
  }

  const roundedDeltaPoints = Number(((latest - previous) * 100).toFixed(1));

  if (roundedDeltaPoints > 0) {
    return { bg: "success", label: `+${roundedDeltaPoints.toFixed(1)} pts` };
  }

  if (roundedDeltaPoints < 0) {
    return { bg: "danger", label: `${roundedDeltaPoints.toFixed(1)} pts` };
  }

  return { bg: "secondary", label: "0.0 pts" };
};

const MarketBreadthCard: React.FC<MarketBreadthCardProps> = ({
  marketBreadth,
  marketBreadthMa,
  strengthIndex,
  timestamps,
}) => {
  const latestMarketBreadth = marketBreadth[0];
  const marketBreadthIsPositive =
    typeof latestMarketBreadth === "number" && latestMarketBreadth > 0;
  const deltaBadge = resolveDeltaBadge(marketBreadthMa);
  const chartTimestamps = [...timestamps].reverse();
  const chartMarketBreadth = [...marketBreadth].reverse();
  const chartMarketBreadthMa = marketBreadthMa
    ? [...marketBreadthMa].reverse()
    : [];
  const chartStrengthIndex = strengthIndex ? [...strengthIndex].reverse() : [];

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i
              className={`fs-2 fa fa-suitcase ${marketBreadthIsPositive ? "text-success" : "text-danger"}`}
            />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title
              as="h5"
              className="mt-0 d-flex align-items-center gap-2"
            >
              <span>Market Breadth Trend</span>
              <Badge bg={deltaBadge.bg}>{deltaBadge.label}</Badge>
            </Card.Title>
            <p className="u-text-left">
              Shows the Advancers-Decliners ratio (market breadth).
              <br />
              Over 0 indicates positive reversal Under 0 indicates negative
              reversal.
            </p>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        <PlotlyChart
          data={[
            {
              x: chartTimestamps,
              y: chartMarketBreadth,
              type: "scatter",
              mode: "lines+markers",
              name: "Market Breadth",
              line: { color: "#007bff", width: 2 },
              marker: { size: 6 },
              fill: "tozeroy",
              fillcolor: marketBreadthIsPositive ? "#28a74533" : "#dc354533",
            },
            ...(chartMarketBreadthMa.length > 0
              ? [
                  {
                    x: chartTimestamps,
                    y: chartMarketBreadthMa,
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Breadth Trend",
                    line: { color: "#20c997", width: 3 },
                    marker: { size: 5 },
                    fill: "none",
                  },
                ]
              : []),
            ...(strengthIndex && strengthIndex.length > 0
              ? [
                  {
                    x: chartTimestamps,
                    y: chartStrengthIndex,
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Strength Index",
                    line: { color: "#ff9900", width: 2, dash: "dot" },
                    marker: { size: 6 },
                    fill: "none",
                  },
                ]
              : []),
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { t: 30, l: 40, r: 20, b: 40 },
            xaxis: {
              title: "Time",
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: "Market Breadth",
              showgrid: true,
              zeroline: true,
              zerolinecolor: "#6c757d",
              zerolinewidth: 1,
            },
            legend: { orientation: "h", y: -0.2 },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler={true}
        />
      </Card.Body>
      <Card.Footer className="text-muted">
        <hr />

        {timestamps && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {moment(timestamps[0]).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default MarketBreadthCard;
