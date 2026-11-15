import { useMemo } from "react";
import { Card } from "react-bootstrap";
import type { CvdAggregate } from "../../features/marketApiSlice";
import LivePlotlyChart from "./LivePlotlyChart";

interface StoredCvdCardProps {
  result?: CvdAggregate;
  isLoading: boolean;
  isError: boolean;
  symbol?: string;
}

const StoredCvdCard = ({
  result,
  isLoading,
  isError,
  symbol,
}: StoredCvdCardProps) => {
  const subject = symbol ? `${symbol} CVD` : "Market CVD";
  const changeLabel = symbol
    ? "Contract multiplier changed"
    : "Universe changed";
  const data = useMemo(() => {
    const points = result?.data ?? [];
    const chartPoints = points.flatMap((point, index) => {
      const previous = points[index - 1];
      return previous && (previous.gap || point.gap || point.universe_changed)
        ? [null, point]
        : [point];
    });
    return [
      {
        type: "scatter",
        mode: "lines+markers",
        connectgaps: false,
        x: chartPoints.map((point) => point?.timestamp ?? null),
        y: chartPoints.map((point) => point?.cvd ?? null),
        ids: chartPoints.map(
          (point, index) => point?.timestamp ?? `gap-${index}`,
        ),
        line: { color: "#51cbce", width: 2 },
        marker: {
          size: 5,
          symbol: chartPoints.map((point) =>
            point?.complete ? "circle" : "diamond-open",
          ),
          color: chartPoints.map((point) =>
            point?.complete ? "#51cbce" : "#ffc107",
          ),
        },
        customdata: chartPoints.map((point) =>
          point
            ? [
                point.buy,
                point.sell,
                point.covered_symbols,
                point.expected_symbols,
                point.current
                  ? "Current interval (partial)"
                  : point.complete
                    ? "Complete"
                    : "Partial coverage",
                point.universe_changed ? changeLabel : "",
              ]
            : [],
        ),
        text: chartPoints.map((point) =>
          point
            ? `${point.timestamp}<br>Observed CVD: ${point.cvd ?? "Missing"} USDT<br>Buy: ${point.buy ?? "Missing"} USDT<br>Sell: ${point.sell ?? "Missing"} USDT<br>Covered / expected symbols: ${point.covered_symbols} / ${point.expected_symbols ?? "Unknown"}<br>${point.current ? "Current interval (partial)" : point.complete ? "Complete" : "Partial coverage"}${point.universe_changed ? ` · ${changeLabel}` : ""}`
            : "",
        ),
        hovertemplate: "%{text}<extra></extra>",
        name: subject,
      },
    ];
  }, [result, subject, changeLabel]);
  const layout = useMemo(
    () => ({
      autosize: true,
      height: 380,
      showlegend: false,
      margin: { t: 20, l: 90, r: 20, b: 60 },
      xaxis: {
        type: "date",
        title: {
          text: `UTC time · ${symbol ? "1-minute" : "15-minute"} intervals`,
        },
      },
      yaxis: { title: { text: "Observed CVD (USDT)" }, zeroline: true },
    }),
    [symbol],
  );
  return (
    <Card className="card-chart">
      <Card.Header>
        <Card.Title as="h5">
          {symbol
            ? "Cumulative Volume Delta"
            : "Market Cumulative Volume Delta"}
        </Card.Title>
        <p className="text-body-secondary mb-0">
          {symbol
            ? `${symbol} · KuCoin futures. `
            : "Registered active linear USDT KuCoin futures. "}
          Aggressive buy minus sell USDT notional, weighted by traded size.
        </p>
      </Card.Header>
      <Card.Body>
        <div style={{ minHeight: layout.height }}>
          {isLoading && (
            <p role="status">
              Loading {symbol ? `${symbol} CVD` : "market CVD"}…
            </p>
          )}
          {isError && <p role="alert">{subject} could not be refreshed.</p>}
          {result?.stale && (
            <p role="status" className="text-warning">
              Collector checkpoint is stale. Recent executions may be missing.
            </p>
          )}
          {!isLoading && !isError && !result?.data.length && (
            <p>
              Collection has no observations yet{symbol ? ` for ${symbol}` : ""}
              .
            </p>
          )}
          {result?.partial && (
            <p className="text-warning">
              Partial coverage: open diamonds mark incomplete intervals. Lines
              break at gaps and {symbol ? "contract multiplier" : "universe"}{" "}
              changes; CVD includes only observed trades.
            </p>
          )}
          {!!result?.data.length && (
            <LivePlotlyChart data={data} layout={layout} />
          )}
        </div>
      </Card.Body>
      <Card.Footer className="text-body-secondary">
        {symbol ? "Rolling 15-minute" : "Seven-day"} window; CVD starts at zero
        at{" "}
        {result?.reset_at
          ? new Date(result.reset_at).toISOString()
          : "the window start"}{" "}
        and accumulates observed deltas. Central collection starts at
        deployment; outages have no backfill. The current interval is partial;
        closed minutes allow two minutes for late arrivals.
        {result?.updated_at &&
          ` Last checkpoint: ${new Date(result.updated_at).toISOString()}.`}
      </Card.Footer>
    </Card>
  );
};

export default StoredCvdCard;
