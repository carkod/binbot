import moment from "moment";
import { type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import type {
  GainersLosersSnapshot,
  TopMover,
} from "../../features/marketApiSlice";
import { roundDecimals } from "../../utils/math";
import PlotlyChart from "./PlotlyChart";

type GainersLosersSeriesCardProps = {
  snapshots: GainersLosersSnapshot[];
};

const averagePriceChange = (movers: TopMover[]): number | null => {
  if (movers.length === 0) return null;

  return (
    movers.reduce((total, mover) => total + mover.price_change_percent, 0) /
    movers.length
  );
};

const formatMovers = (movers: TopMover[]) =>
  movers
    .map(
      ({ symbol, price_change_percent }) =>
        `${symbol}: ${price_change_percent > 0 ? "+" : ""}${roundDecimals(price_change_percent, 2)}%`,
    )
    .join("<br>");

const resolveMomentumBadge = (snapshot: GainersLosersSnapshot) => {
  const averageGain = averagePriceChange(snapshot.top_gainers);
  const averageLoss = averagePriceChange(snapshot.top_losers);

  if (averageGain === null || averageLoss === null) {
    return { bg: "secondary", label: "N/A" };
  }

  const netMomentum = roundDecimals(averageGain + averageLoss, 1);
  const prefix = netMomentum > 0 ? "+" : "";

  return {
    bg: netMomentum > 0 ? "success" : netMomentum < 0 ? "danger" : "secondary",
    label: `${prefix}${netMomentum.toFixed(1)} pts net`,
  };
};

const GainersLosersSeriesCard: FC<GainersLosersSeriesCardProps> = ({
  snapshots,
}) => {
  const chronologicalSnapshots = [...snapshots].reverse();
  const timestamps = chronologicalSnapshots.map(
    (snapshot) => snapshot.recorded_at,
  );
  const averageGains = chronologicalSnapshots.map((snapshot) =>
    averagePriceChange(snapshot.top_gainers),
  );
  const averageLosses = chronologicalSnapshots.map((snapshot) =>
    averagePriceChange(snapshot.top_losers),
  );
  const gainersHoverText = chronologicalSnapshots.map((snapshot) =>
    formatMovers(snapshot.top_gainers),
  );
  const losersHoverText = chronologicalSnapshots.map((snapshot) =>
    formatMovers(snapshot.top_losers),
  );
  const momentumBadge = resolveMomentumBadge(snapshots[0]);

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i className="fs-2 fa fa-chart-line text-info" />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title
              as="h5"
              className="mt-0 d-flex align-items-center gap-2"
            >
              <span>Top Gainers &amp; Losers Trend</span>
              <Badge bg={momentumBadge.bg}>{momentumBadge.label}</Badge>
            </Card.Title>
            <p className="u-text-left">
              Average 24h change for the top KuCoin futures movers.
              <br />
              Hover over a point to see every symbol in that snapshot.
            </p>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        <PlotlyChart
          data={[
            {
              x: timestamps,
              y: averageGains,
              text: gainersHoverText,
              type: "scatter",
              mode: "lines+markers",
              name: "Top gainers average",
              line: { color: "#28a745", width: 2 },
              marker: { size: 6 },
              fill: "tozeroy",
              fillcolor: "#28a74533",
              hovertemplate:
                "%{x|%d/%m %H:%M}<br>Average: %{y:.2f}%<br>%{text}<extra>Top gainers</extra>",
            },
            {
              x: timestamps,
              y: averageLosses,
              text: losersHoverText,
              type: "scatter",
              mode: "lines+markers",
              name: "Top losers average",
              line: { color: "#dc3545", width: 2 },
              marker: { size: 6 },
              fill: "tozeroy",
              fillcolor: "#dc354533",
              hovertemplate:
                "%{x|%d/%m %H:%M}<br>Average: %{y:.2f}%<br>%{text}<extra>Top losers</extra>",
            },
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { t: 30, l: 45, r: 20, b: 40 },
            xaxis: {
              title: "Time",
              tickformat: "%d/%m %H:%M",
              showgrid: false,
            },
            yaxis: {
              title: "24h change (%)",
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
        <div className="card-stats">
          <i className="fa fa-check" /> Last updated{" "}
          {moment(snapshots[0].recorded_at).format("DD/MM/YYYY HH:mm")}
        </div>
      </Card.Footer>
    </Card>
  );
};

export default GainersLosersSeriesCard;
