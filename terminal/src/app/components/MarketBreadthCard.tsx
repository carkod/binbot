import { Badge, Card, Row, Col } from "react-bootstrap";
import moment from "moment";
import PlotlyChart from "./PlotlyChart";
import { roundDecimals } from "../../utils/math";
import type { FC } from "react";

type MarketBreadthCardProps = {
  medianReturn15m?: Array<number | null>;
  medianReturn1h?: Array<number | null>;
  medianReturn3h?: Array<number | null>;
  fallingShare1h?: Array<number | null>;
  fallingShare3h?: Array<number | null>;
  timestamps: string[];
};

const resolveMedianBadge = (latest?: number | null) => {
  if (latest === null || latest === undefined || !Number.isFinite(latest)) {
    return { bg: "secondary", label: "15m: N/A" };
  }

  const rounded = roundDecimals(latest, 2);
  return {
    bg: latest > 0 ? "success" : latest < 0 ? "danger" : "secondary",
    label: `15m: ${rounded > 0 ? "+" : ""}${rounded.toFixed(2)}%`,
  };
};

const MarketBreadthCard: FC<MarketBreadthCardProps> = ({
  medianReturn15m,
  medianReturn1h,
  medianReturn3h,
  fallingShare1h,
  fallingShare3h,
  timestamps,
}) => {
  const medianBadge = resolveMedianBadge(medianReturn15m?.[0]);
  const chartTimestamps = [...timestamps].reverse();
  const chartMedianReturn15m = medianReturn15m
    ? [...medianReturn15m].reverse()
    : [];
  const chartMedianReturn1h = medianReturn1h
    ? [...medianReturn1h].reverse()
    : [];
  const chartMedianReturn3h = medianReturn3h
    ? [...medianReturn3h].reverse()
    : [];
  const hasRecentReturns =
    chartMedianReturn15m.some((value) => value !== null) ||
    chartMedianReturn1h.some((value) => value !== null) ||
    chartMedianReturn3h.some((value) => value !== null);

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i className={`fs-2 fa fa-suitcase text-${medianBadge.bg}`} />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title
              as="h5"
              className="mt-0 d-flex align-items-center gap-2"
            >
              <span>Market Breadth Trend</span>
              <Badge bg={medianBadge.bg}>{medianBadge.label}</Badge>
            </Card.Title>
            <p className="u-text-left">
              Median futures price returns over 15m, 1h, and 3h. Below zero
              means the typical contract fell during that window.
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
        {hasRecentReturns ? (
          <PlotlyChart
            data={[
              ...(chartMedianReturn15m.some((value) => value !== null)
                ? [
                    {
                      x: chartTimestamps,
                      y: chartMedianReturn15m,
                      type: "scatter",
                      mode: "lines+markers",
                      name: "Median return (15m)",
                      line: { color: "#007bff", width: 2 },
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
                    },
                  ]
                : []),
            ]}
            layout={{
              autosize: true,
              height: 460,
              margin: { t: 30, l: 90, r: 20, b: 135 },
              xaxis: {
                title: { text: "Time", standoff: 14 },
                automargin: true,
                tickformat: "%d/%m %H:%M",
                showgrid: false,
              },
              yaxis: {
                title: { text: "Median return (%)", standoff: 14 },
                automargin: true,
                ticksuffix: "%",
                showgrid: true,
                zeroline: true,
                zerolinecolor: "#6c757d",
                zerolinewidth: 1,
              },
              legend: {
                orientation: "h",
                x: 0.5,
                xanchor: "center",
                y: -0.31,
                yanchor: "top",
              },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%", height: "100%" }}
            useResizeHandler={true}
          />
        ) : (
          <div className="text-body-secondary">
            Waiting for futures price snapshots.
          </div>
        )}
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
