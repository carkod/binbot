import { Badge, Button, Card } from "react-bootstrap";
import {
  OBI_WINDOW_MS,
  type ObiSnapshot,
} from "../../features/kucoinLiquidity";
import { useOrderBookHistory } from "../hooks/useOrderBookHistory";
import PlotlyChart from "./PlotlyChart";

interface OrderBookImbalanceCardProps {
  snapshot?: ObiSnapshot;
  enabled: boolean;
  isFetching: boolean;
  isError: boolean;
  onRetry: () => void;
}

const OrderBookImbalanceCard = ({
  snapshot,
  enabled,
  isFetching,
  isError,
  onRetry,
}: OrderBookImbalanceCardProps) => {
  const { history, chartPoints, now } = useOrderBookHistory(
    snapshot,
    enabled,
    isError,
  );
  const hasObi = history.some(({ obi }) => obi !== null);

  return (
    <Card className="card-chart">
      <Card.Header>
        <Card.Title
          as="h5"
          className="mt-0 d-flex flex-wrap align-items-center gap-2"
        >
          <span>Order Book Imbalance (OBI)</span>
          <span aria-live="polite">
            {enabled &&
              !isError &&
              snapshot &&
              snapshot.timestamp >= now - OBI_WINDOW_MS && (
                <Badge
                  bg={
                    snapshot.liquidity === "High liquidity"
                      ? "success"
                      : "danger"
                  }
                >
                  {snapshot.liquidity}
                </Badge>
              )}
          </span>
        </Card.Title>
        <p className="text-body-secondary mb-0">
          Last 15 minutes. Above zero: more bid depth. Below zero: more ask
          depth.
        </p>
      </Card.Header>
      <Card.Body>
        {!enabled ? (
          <p className="text-body-secondary">Enter a symbol</p>
        ) : (
          <>
            {isError && (
              <div role="status" className="mb-3">
                Liquidity unavailable.{" "}
                <Button variant="link" onClick={onRetry}>
                  Retry
                </Button>
              </div>
            )}
            {hasObi ? (
              <PlotlyChart
                data={[
                  {
                    x: chartPoints.map(({ timestamp }) =>
                      new Date(timestamp).toISOString(),
                    ),
                    y: chartPoints.map(({ obi }) =>
                      obi === null ? null : obi * 100,
                    ),
                    type: "scatter",
                    mode: "lines+markers",
                    name: "OBI",
                    line: { color: "#51cbce", width: 2 },
                    marker: { size: 4 },
                    connectgaps: false,
                    hovertemplate:
                      "%{x|%H:%M:%S}<br>OBI: %{y:+.1f}%<extra></extra>",
                  },
                ]}
                layout={{
                  autosize: true,
                  height: 380,
                  margin: { t: 20, l: 75, r: 20, b: 60 },
                  xaxis: {
                    title: { text: "Time" },
                    type: "date",
                    tickformat: "%H:%M:%S",
                    range: [
                      new Date(now - OBI_WINDOW_MS).toISOString(),
                      new Date(now).toISOString(),
                    ],
                    showgrid: false,
                  },
                  yaxis: {
                    title: { text: "OBI (%)" },
                    range: [-100, 100],
                    zeroline: true,
                    zerolinecolor: "#6c757d",
                    zerolinewidth: 2,
                    showgrid: true,
                  },
                  showlegend: false,
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: "100%", height: "100%" }}
                useResizeHandler={true}
              />
            ) : (
              !isError && (
                <p className="text-body-secondary" role="status">
                  {isFetching
                    ? "Checking order book…"
                    : "Waiting for order-book depth."}
                </p>
              )
            )}
          </>
        )}
      </Card.Body>
      <Card.Footer className="text-body-secondary">
        History collects while this page is open and resets on reload or symbol
        change.
      </Card.Footer>
    </Card>
  );
};

export default OrderBookImbalanceCard;
