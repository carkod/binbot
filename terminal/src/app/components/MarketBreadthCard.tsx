import { Badge, Card, Row, Col } from "react-bootstrap";
import moment from "moment";
import PlotlyChart from "./PlotlyChart";
import { roundDecimals } from "../../utils/math";
import type { FC } from "react";

// Olive gold: a mix of the gainers (green) and losers (red) ranking colours,
// darkened so the line keeps 3:1 contrast on the card surface.
const CUMULATIVE_BREADTH_COLOR = "#9a8500";
const CUMULATIVE_BREADTH_EMA_COLOR = "#2563eb";
// Samples are 15 minutes apart, so four samples back is one hour.
const SAMPLES_PER_HOUR = 4;

type MarketBreadthCardProps = {
  cumulativeBreadth?: Array<number | null>;
  cumulativeBreadthEma?: Array<number | null>;
  timestamps: string[];
};

const isNumber = (value?: number | null): value is number =>
  value !== null && value !== undefined && Number.isFinite(value);

const resolveTrend = (latest?: number | null, latestEma?: number | null) => {
  if (!isNumber(latest) || !isNumber(latestEma)) {
    return { bg: "secondary", label: "Trend: N/A" };
  }
  if (latest > latestEma) {
    return { bg: "success", label: "Trend: rising" };
  }
  if (latest < latestEma) {
    return { bg: "danger", label: "Trend: falling" };
  }
  return { bg: "secondary", label: "Trend: flat" };
};

const MarketBreadthCard: FC<MarketBreadthCardProps> = ({
  cumulativeBreadth,
  cumulativeBreadthEma,
  timestamps,
}) => {
  const latest = cumulativeBreadth?.[0];
  const hourAgo = cumulativeBreadth?.[SAMPLES_PER_HOUR];
  const trend = resolveTrend(latest, cumulativeBreadthEma?.[0]);
  const lastHourChange =
    isNumber(latest) && isNumber(hourAgo)
      ? roundDecimals(latest - hourAgo, 0)
      : null;
  const chartTimestamps = [...timestamps].reverse();
  const chartCumulativeBreadth = cumulativeBreadth
    ? [...cumulativeBreadth].reverse()
    : [];
  const chartCumulativeBreadthEma = cumulativeBreadthEma
    ? [...cumulativeBreadthEma].reverse()
    : [];
  const hasCumulativeBreadth = chartCumulativeBreadth.some(
    (value) => value !== null,
  );

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i className={`fs-2 fa fa-suitcase text-${trend.bg}`} />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title
              as="h5"
              className="mt-0 d-flex align-items-center gap-2"
            >
              <span>Market Breadth Trend</span>
              <Badge bg={trend.bg}>{trend.label}</Badge>
            </Card.Title>
            <p className="u-text-left">
              Running total of the futures market&apos;s net breadth. Every 15
              minutes, it adds the share of contracts that rose minus the share
              that fell, weighted by √turnover. Read it like a price chart: the
              direction is the trend, the level has no meaning.
            </p>
            {lastHourChange !== null && (
              <div className="small text-body-secondary">
                {`Last 1h: ${lastHourChange > 0 ? "+" : ""}${lastHourChange.toFixed(0)}`}
              </div>
            )}
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {hasCumulativeBreadth ? (
          <PlotlyChart
            data={[
              {
                x: chartTimestamps,
                y: chartCumulativeBreadth,
                type: "scatter",
                mode: "lines",
                name: "Cumulative breadth",
                line: { color: CUMULATIVE_BREADTH_COLOR, width: 2 },
                hovertemplate: "%{y:+.0f}<extra>Cumulative breadth</extra>",
              },
              ...(chartCumulativeBreadthEma.some((value) => value !== null)
                ? [
                    {
                      x: chartTimestamps,
                      y: chartCumulativeBreadthEma,
                      type: "scatter",
                      mode: "lines",
                      name: "EMA (4h)",
                      line: { color: CUMULATIVE_BREADTH_EMA_COLOR, width: 2 },
                      hovertemplate: "%{y:+.0f}<extra>EMA (4h)</extra>",
                    },
                  ]
                : []),
            ]}
            layout={{
              autosize: true,
              height: 460,
              margin: { t: 30, l: 90, r: 20, b: 135 },
              hovermode: "x unified",
              xaxis: {
                title: { text: "Time", standoff: 14 },
                automargin: true,
                tickformat: "%d/%m %H:%M",
                showgrid: false,
              },
              yaxis: {
                title: { text: "Cumulative net breadth", standoff: 14 },
                automargin: true,
                tickformat: "+d",
                showgrid: true,
                zeroline: false,
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
