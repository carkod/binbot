import { useMemo } from "react";
import { Button, Card } from "react-bootstrap";
import { OBI_WINDOW_MS } from "../../features/kucoinLiquidity";
import type { useOrderBookHistory } from "../hooks/useOrderBookHistory";
import LivePlotlyChart from "./LivePlotlyChart";

interface SpreadAndDepthCardProps {
  orderBookHistory: ReturnType<typeof useOrderBookHistory>;
  enabled: boolean;
  isFetching: boolean;
  isError: boolean;
  onRetry: () => void;
}

const SpreadAndDepthCard = ({
  orderBookHistory,
  enabled,
  isFetching,
  isError,
  onRetry,
}: SpreadAndDepthCardProps) => {
  const { history, chartPoints, now } = orderBookHistory;

  const data = useMemo(() => {
    const timestamps = chartPoints.map(({ timestamp }) =>
      new Date(timestamp).toISOString(),
    );
    return [
      {
        ids: chartPoints.map(({ timestamp }) => String(timestamp)),
        x: timestamps,
        y: chartPoints.map(({ bidDepth }) => bidDepth),
        type: "scatter",
        mode: "lines+markers",
        name: "Bid depth",
        line: { color: "#198754", width: 2 },
        marker: { size: 4 },
        connectgaps: false,
        hovertemplate:
          "%{x|%H:%M:%S}<br>Bid depth: %{y:,.2f} USDT<extra></extra>",
      },
      {
        ids: chartPoints.map(({ timestamp }) => String(timestamp)),
        x: timestamps,
        y: chartPoints.map(({ askDepth }) => askDepth),
        type: "scatter",
        mode: "lines+markers",
        name: "Ask depth",
        line: { color: "#dc3545", width: 2 },
        marker: { size: 4 },
        connectgaps: false,
        hovertemplate:
          "%{x|%H:%M:%S}<br>Ask depth: %{y:,.2f} USDT<extra></extra>",
      },
      {
        ids: chartPoints.map(({ timestamp }) => String(timestamp)),
        x: timestamps,
        y: chartPoints.map(({ spreadRatio }) =>
          spreadRatio === null ? null : spreadRatio * 100,
        ),
        yaxis: "y2",
        type: "scatter",
        mode: "lines+markers",
        name: "Spread",
        line: { color: "#51cbce", width: 2, dash: "dot" },
        marker: { size: 4 },
        connectgaps: false,
        hovertemplate: "%{x|%H:%M:%S}<br>Spread: %{y:.4f}%<extra></extra>",
      },
    ];
  }, [chartPoints]);
  const layout = useMemo(
    () => ({
      autosize: true,
      height: 380,
      margin: { t: 20, l: 90, r: 85, b: 80 },
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
        title: { text: "Nearby depth (USDT)" },
        rangemode: "tozero",
      },
      yaxis2: {
        title: { text: "Spread (%)" },
        overlaying: "y",
        side: "right",
        rangemode: "tozero",
        showgrid: false,
      },
      legend: { orientation: "h", y: -0.25 },
      showlegend: true,
    }),
    [now],
  );

  return (
    <Card className="card-chart">
      <Card.Header>
        <Card.Title as="h5" className="mt-0">
          Spread and Nearby Depth
        </Card.Title>
        <p className="text-body-secondary mb-0">
          Last 15 minutes. Spread as a percentage of the midpoint; bid and ask
          depth within ±0.5% of the midpoint, valued in USDT.
        </p>
      </Card.Header>
      <Card.Body>
        {!enabled ? (
          <p className="text-body-secondary">Enter a symbol</p>
        ) : (
          <>
            {isError && (
              <div role="status" className="mb-3">
                Spread and depth unavailable.{" "}
                <Button variant="link" onClick={onRetry}>
                  Retry
                </Button>
              </div>
            )}
            {history.length > 0 ? (
              <LivePlotlyChart data={data} layout={layout} />
            ) : (
              !isError && (
                <p className="text-body-secondary" role="status">
                  {isFetching
                    ? "Checking spread and depth…"
                    : "Waiting for order-book depth."}
                </p>
              )
            )}
          </>
        )}
      </Card.Body>
      <Card.Footer className="text-body-secondary">
        Visible depth from up to 100 levels per side. History collects across
        navigation while the terminal is open for the selected symbol. Resets on
        reload or symbol change.
      </Card.Footer>
    </Card>
  );
};

export default SpreadAndDepthCard;
