import { Box, Card, Group, Text, Title } from "@mantine/core";
import { useMemo } from "react";
import type { CvdAggregate } from "../../features/marketApiSlice";
import LivePlotlyChart from "./LivePlotlyChart";
interface StoredCvdCardProps {
  result?: CvdAggregate;
  isLoading: boolean;
  isError: boolean;
  symbol?: string;
  embedded?: boolean;
}
const StoredCvdCard = ({
  result,
  isLoading,
  isError,
  symbol,
  embedded = false,
}: StoredCvdCardProps) => {
  const Container = embedded ? Box : Card;
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
    () => {
      const now = Date.now();
      return {
        autosize: true,
        height: 380,
        showlegend: false,
        margin: { t: 20, l: 105, r: 20, b: 60 },
        xaxis: {
          type: "date",
          autorange: !!symbol,
          ...(!symbol && {
            range: [
              new Date(now - 6 * 60 * 60 * 1000).toISOString(),
              new Date(now).toISOString(),
            ],
          }),
          uirevision: false,
          title: {
            text: `${symbol ? "1-minute" : "15-minute"} intervals`,
          },
        },
        yaxis: {
          autorange: true,
          uirevision: false,
          title: { text: "Observed CVD (USDT)", standoff: 24 },
          automargin: true,
          zeroline: true,
        },
      };
    },
    // Plotly mutates axis ranges after zooming. Fresh axes let each snapshot
    // refit the rolling window without remounting the chart.
    [symbol, result],
  );
  return (
    <Container mb={embedded ? 0 : "md"}>
      <Box mb="sm">
        <Title order={5}>
          {symbol
            ? "Cumulative Volume Delta"
            : "Market Cumulative Volume Delta"}
        </Title>
        <Text c="dimmed" mb={0}>
          {!symbol && "Registered active linear USDT KuCoin futures. "}
          Aggressive buy minus sell USDT notional, weighted by traded size.
        </Text>
      </Box>
      <Box mih={layout.height}>
        {isLoading && (
          <Text role="status">
            Loading {symbol ? `${symbol} CVD` : "market CVD"}…
          </Text>
        )}
        {isError && <Text role="alert">{subject} could not be refreshed.</Text>}
        {result?.stale && (
          <Text role="status" c="warning.9">
            Collector checkpoint is stale. Recent executions may be missing.
          </Text>
        )}
        {!isLoading && !isError && !result?.data.length && (
          <Text>
            Collection has no observations yet{symbol ? ` for ${symbol}` : ""}.
          </Text>
        )}
        {result?.partial && (
          <Text c="warning.9">
            Partial coverage: open diamonds mark incomplete intervals. Lines
            break at gaps and {symbol ? "contract multiplier" : "universe"}{" "}
            changes; CVD includes only observed trades.
          </Text>
        )}
        {!!result?.data.length && (
          <LivePlotlyChart data={data} layout={layout} />
        )}
      </Box>
      <Group mt="sm" c="dimmed">
        {!symbol && "Showing the last 6 hours. "}
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
      </Group>
    </Container>
  );
};
export default StoredCvdCard;
