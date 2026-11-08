import { Badge, Card, Row, Col } from "react-bootstrap";
import moment from "moment";
import PlotlyChart from "./PlotlyChart";
import { roundDecimals } from "../../utils/math";
import type { FC } from "react";

type MarketBreadthCardProps = {
  marketBreadth: number[];
  marketBreadthMa?: Array<number | null>;
  medianReturn1h?: Array<number | null>;
  medianReturn3h?: Array<number | null>;
  fallingShare1h?: Array<number | null>;
  fallingShare3h?: Array<number | null>;
  timestamps: string[];
};

const resolveDeltaBadge = (marketBreadthMa?: Array<number | null>) => {
  const latest = marketBreadthMa?.[0];
  const previous = marketBreadthMa?.[1];

  if (
    latest === null ||
    latest === undefined ||
    previous === null ||
    previous === undefined ||
    !Number.isFinite(latest) ||
    !Number.isFinite(previous)
  ) {
    return { bg: "secondary", label: "N/A" };
  }

  const roundedDeltaPoints = roundDecimals((latest - previous) * 100, 1);

  if (roundedDeltaPoints > 0) {
    return { bg: "success", label: `+${roundedDeltaPoints.toFixed(1)} pts` };
  }

  if (roundedDeltaPoints < 0) {
    return { bg: "danger", label: `${roundedDeltaPoints.toFixed(1)} pts` };
  }

  return { bg: "secondary", label: "0.0 pts" };
};

const MarketBreadthCard: FC<MarketBreadthCardProps> = ({
  marketBreadth,
  marketBreadthMa,
  medianReturn1h,
  medianReturn3h,
  fallingShare1h,
  fallingShare3h,
  timestamps,
}) => {
  const marketBreadthIsPositive = marketBreadth[0] > 0;
  const deltaBadge = resolveDeltaBadge(marketBreadthMa);
  const chartTimestamps = [...timestamps].reverse();
  const chartMarketBreadth = [...marketBreadth].reverse();
  const chartMarketBreadthMa = marketBreadthMa
    ? [...marketBreadthMa].reverse()
    : [];
  const chartMedianReturn1h = medianReturn1h
    ? [...medianReturn1h].reverse()
    : [];
  const chartMedianReturn3h = medianReturn3h
    ? [...medianReturn3h].reverse()
    : [];
  const hasRecentReturns =
    chartMedianReturn1h.some((value) => value !== null) ||
    chartMedianReturn3h.some((value) => value !== null);

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
              The 24h line shows the Advancers-Decliners ratio. Recent lines
              show the median futures price return over 1h and 3h.
              <br />
              Above 0 means more assets are up over 24h; below 0 means more are
              down.
            </p>
            {fallingShare1h?.[0] != null && medianReturn1h?.[0] != null && (
              <div className="small text-body-secondary">
                1h: {roundDecimals(fallingShare1h[0] * 100, 1)}% falling ·
                median {roundDecimals(medianReturn1h[0], 2)}%
              </div>
            )}
            {fallingShare3h?.[0] != null && medianReturn3h?.[0] != null && (
              <div className="small text-body-secondary">
                3h: {roundDecimals(fallingShare3h[0] * 100, 1)}% falling ·
                median {roundDecimals(medianReturn3h[0], 2)}%
              </div>
            )}
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
            ...(chartMarketBreadthMa.some((value) => value !== null)
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
            ...(chartMedianReturn1h.some((value) => value !== null)
              ? [
                  {
                    x: chartTimestamps,
                    y: chartMedianReturn1h,
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Median return (1h)",
                    line: { color: "#ff9900", width: 2, dash: "dot" },
                    marker: { size: 6 },
                    fill: "none",
                    yaxis: "y2",
                  },
                ]
              : []),
            ...(chartMedianReturn3h.some((value) => value !== null)
              ? [
                  {
                    x: chartTimestamps,
                    y: chartMedianReturn3h,
                    type: "scatter",
                    mode: "lines+markers",
                    name: "Median return (3h)",
                    line: { color: "#6f42c1", width: 2, dash: "dot" },
                    marker: { size: 6 },
                    fill: "none",
                    yaxis: "y2",
                  },
                ]
              : []),
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { t: 30, l: 40, r: 70, b: 40 },
            xaxis: {
              title: "Time",
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: "24h breadth",
              showgrid: true,
              zeroline: true,
              zerolinecolor: "#6c757d",
              zerolinewidth: 1,
            },
            ...(hasRecentReturns
              ? {
                  yaxis2: {
                    title: "Median return (%)",
                    overlaying: "y",
                    side: "right",
                    ticksuffix: "%",
                    zeroline: true,
                    zerolinecolor: "#6c757d",
                  },
                }
              : {}),
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
