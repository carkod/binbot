import moment from "moment";
import { Badge, Card, Col, Row } from "react-bootstrap";
import type { FC } from "react";
import type { GainersLosersAggregatePoint } from "../../features/marketApiSlice";
import PlotlyChart from "./PlotlyChart";

type GainersLosersHistoryCardProps = {
  points: GainersLosersAggregatePoint[];
};

const GAINER_COLOR = "#28a745";
const LOSER_COLOR = "#dc3545";

const GainersLosersHistoryCard: FC<GainersLosersHistoryCardProps> = ({
  points,
}) => {
  const history = [...points]
    .sort(
      (left, right) =>
        new Date(left.timestamp).getTime() -
        new Date(right.timestamp).getTime(),
    )
    .map((point) => {
      const gain = point.gainer_magnitude;
      const loss = point.loser_magnitude;
      const magnitude = gain + loss;
      return {
        timestamp: point.timestamp,
        gain,
        loss,
        gainShare: magnitude > 0 ? (gain / magnitude) * 100 : null,
        lossShare: magnitude > 0 ? (loss / magnitude) * 100 : null,
        advancers: point.advancers,
        decliners: point.decliners,
      };
    });
  const latest = history.at(-1);
  const hasHistory = history.some((point) => point.gainShare !== null);
  const timestamps = history.map((point) => point.timestamp);
  const hoverData = history.map((point) => [
    point.gainShare ?? 0,
    point.lossShare ?? 0,
    point.gain + point.loss,
    point.advancers,
    point.decliners,
  ]);

  return (
    <Card className="card-chart">
      <Card.Header>
        <Row>
          <Col lg="1" md="1" sm="1">
            <i className="fs-2 fa fa-chart-area text-success" />
          </Col>
          <Col lg="11" md="11" sm="11">
            <Card.Title
              as="h5"
              className="mt-0 d-flex align-items-center gap-2"
            >
              <span>Gainers vs Losers Trend</span>
              {latest?.gainShare !== null &&
                latest?.gainShare !== undefined && (
                  <Badge bg={latest.gainShare >= 50 ? "success" : "danger"}>
                    Gainers {latest.gainShare.toFixed(1)}%
                  </Badge>
                )}
            </Card.Title>
            <p className="u-text-left mb-0">
              Hourly snapshots of all registered, active KuCoin futures
              contracts. The total height sums their rolling 24h changes; each
              color shows that side&apos;s share.
            </p>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {hasHistory ? (
          <PlotlyChart
            data={[
              {
                x: timestamps,
                y: history.map((point) => point.gain),
                type: "scatter",
                mode: "lines",
                stackgroup: "one",
                name: "Gainers",
                line: { color: GAINER_COLOR, width: 2 },
                fillcolor: "rgba(40,167,69,0.68)",
                customdata: hoverData,
                hovertemplate:
                  "+%{y:.1f} summed pts (%{customdata[0]:.1f}% share)<br>%{customdata[3]:.0f} rising contracts<br>Combined magnitude: %{customdata[2]:.1f} pts<extra>Gainers</extra>",
              },
              {
                x: timestamps,
                y: history.map((point) => point.loss),
                type: "scatter",
                mode: "lines",
                stackgroup: "one",
                name: "Losers",
                line: { color: LOSER_COLOR, width: 2 },
                fillcolor: "rgba(220,53,69,0.68)",
                customdata: hoverData,
                hovertemplate:
                  "−%{y:.1f} summed pts (%{customdata[1]:.1f}% share)<br>%{customdata[4]:.0f} falling contracts<extra>Losers</extra>",
              },
            ]}
            layout={{
              autosize: true,
              height: 460,
              margin: { t: 30, l: 95, r: 20, b: 125 },
              hovermode: "x unified",
              xaxis: {
                title: { text: "Time", standoff: 14 },
                automargin: true,
                tickformat: "%d/%m %H:%M",
                showgrid: false,
              },
              yaxis: {
                title: { text: "Combined 24h magnitude (pts)", standoff: 14 },
                automargin: true,
                rangemode: "tozero",
                showgrid: true,
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
            Waiting for hourly futures price snapshots.
          </div>
        )}
      </Card.Body>
      <Card.Footer className="text-muted">
        <hr />
        {latest && (
          <div className="card-stats">
            <i className="fa fa-check" /> Last updated{" "}
            {moment(latest.timestamp).format("DD/MM/YYYY HH:mm")}
          </div>
        )}
      </Card.Footer>
    </Card>
  );
};

export default GainersLosersHistoryCard;
