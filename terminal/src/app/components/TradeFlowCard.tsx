import { Card } from "react-bootstrap";
import {
  buildTradeFlowSeries,
  type TradeFlowBucket,
} from "../../features/kucoinTradeFlow";
import PlotlyChart from "./PlotlyChart";

interface TradeFlowCardProps {
  kind: "delta" | "cvd";
  buckets: TradeFlowBucket[];
  enabled: boolean;
  status: "connecting" | "live" | "disconnected";
  restarted: boolean;
  storageError?: boolean;
}

const TradeFlowCard = ({
  kind,
  buckets,
  enabled,
  status,
  restarted,
  storageError,
}: TradeFlowCardProps) => {
  const series = buildTradeFlowSeries(buckets);
  const cumulative = kind === "cvd";
  const chartPoints: {
    timestamp: number;
    cvd: number | null;
    delta: number | null;
    buy: number | null;
    sell: number | null;
  }[] = [];
  series.forEach((point, index) => {
    const previous = series[index - 1];
    if (
      previous &&
      (point.gapBefore || point.timestamp - previous.timestamp > 60_000)
    ) {
      chartPoints.push({
        timestamp: previous.timestamp + 30_000,
        cvd: null,
        delta: null,
        buy: null,
        sell: null,
      });
    }
    chartPoints.push(point);
  });
  return (
    <Card className="card-chart">
      <Card.Header>
        <Card.Title as="h5" className="mt-0">
          {cumulative ? "Cumulative Volume Delta" : "Volume Delta"}
        </Card.Title>
        <p className="text-body-secondary mb-0">
          {cumulative
            ? "Accumulated aggressive buy minus sell volume over the displayed window."
            : "Aggressive buy minus sell volume in each minute."}
        </p>
      </Card.Header>
      <Card.Body>
        {!enabled ? (
          <p>Enter a symbol</p>
        ) : (
          <>
            {status !== "live" && (
              <p role="status">
                {status === "connecting"
                  ? "Connecting to live trades…"
                  : "Trade stream disconnected. Reconnecting…"}
              </p>
            )}
            {restarted && (
              <p className="text-warning">
                Previous observations retained. Trades during time away or
                disconnections are missing; affected minutes are partial.
              </p>
            )}
            {storageError && (
              <p role="status" className="text-warning">
                Browser history storage unavailable. Live data may not be saved.
              </p>
            )}
            {series.length > 0 && (
              <PlotlyChart
                data={[
                  {
                    x: chartPoints.map(({ timestamp }) =>
                      new Date(timestamp).toISOString(),
                    ),
                    y: chartPoints.map((point) =>
                      cumulative ? point.cvd : point.delta,
                    ),
                    type: cumulative ? "scatter" : "bar",
                    ...(cumulative
                      ? {
                          mode: "lines+markers",
                          line: { color: "#51cbce", width: 2 },
                          marker: { size: 4 },
                          connectgaps: false,
                        }
                      : {
                          marker: {
                            color: chartPoints.map(({ delta }) =>
                              delta >= 0 ? "#198754" : "#dc3545",
                            ),
                          },
                        }),
                    customdata: chartPoints.map(({ buy, sell }) => [buy, sell]),
                    hovertemplate: `%{x|%H:%M}<br>${cumulative ? "CVD" : "Delta"}: %{y:+,.2f} USDT<br>Buys: %{customdata[0]:,.2f}<br>Sells: %{customdata[1]:,.2f}<extra></extra>`,
                    name: cumulative ? "CVD" : "Volume delta",
                  },
                ]}
                layout={{
                  autosize: true,
                  height: 380,
                  margin: { t: 20, l: 85, r: 20, b: 60 },
                  xaxis: {
                    title: { text: "Time" },
                    type: "date",
                    tickformat: "%H:%M",
                    showgrid: false,
                  },
                  yaxis: {
                    title: {
                      text: cumulative ? "CVD (USDT)" : "Volume delta (USDT)",
                    },
                    zeroline: true,
                    zerolinecolor: "#6c757d",
                    zerolinewidth: 2,
                  },
                  showlegend: false,
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: "100%", height: "100%" }}
                useResizeHandler={true}
              />
            )}
          </>
        )}
      </Card.Body>
      <Card.Footer className="text-body-secondary">
        Observed trades saved per symbol in this browser for the rolling
        15-minute window. Collection pauses when you leave this page; no
        historical backfill. First and current minutes are partial.
      </Card.Footer>
    </Card>
  );
};

export default TradeFlowCard;
