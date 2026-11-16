import { Box, Button, Group, Text, Title } from "@mantine/core";
import { useMemo } from "react";
import type { useOrderBookHistory } from "../hooks/useOrderBookHistory";
import LivePlotlyChart from "./LivePlotlyChart";

interface SpreadAndDepthCardProps {
  orderBookHistory: ReturnType<typeof useOrderBookHistory>;
  enabled: boolean;
  isFetching: boolean;
  isError: boolean;
  onRetry: () => void;
  depthWindowMinutes?: number;
}

const SpreadAndDepthCard = ({
  orderBookHistory,
  enabled,
  isFetching,
  isError,
  onRetry,
  depthWindowMinutes = 15,
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
      margin: { t: 20, l: 105, r: 100, b: 80 },
      xaxis: {
        title: { text: "Time" },
        type: "date",
        tickformat: "%H:%M:%S",
        autorange: false,
        fixedrange: true,
        range: [
          new Date(now - depthWindowMinutes * 60_000).toISOString(),
          new Date(now).toISOString(),
        ],
        showgrid: false,
      },
      yaxis: {
        title: { text: "Nearby depth (USDT)", standoff: 24 },
        automargin: true,
        rangemode: "tozero",
      },
      yaxis2: {
        title: { text: "Spread (%)", standoff: 24 },
        automargin: true,
        overlaying: "y",
        side: "right",
        rangemode: "tozero",
        showgrid: false,
      },
      legend: { orientation: "h", y: -0.25 },
      showlegend: true,
    }),
    [now, depthWindowMinutes],
  );

  return (
    <Box>
      <Box mb="sm">
        <Title order={5} mt={0}>
          Spread and Nearby Depth
        </Title>
        <Text c="dimmed" mb={0}>
          Last {depthWindowMinutes} minutes. Spread as a percentage of the
          midpoint; bid and ask depth within ±0.5% of the midpoint, valued in
          USDT.
        </Text>
      </Box>
      <Box>
        {!enabled ? (
          <Text c="dimmed">Enter a symbol</Text>
        ) : (
          <>
            {isError && (
              <Box role="status" mb={16} component="div">
                Spread and depth unavailable.{" "}
                <Button onClick={onRetry} variant="subtle" type="button">
                  Retry
                </Button>
              </Box>
            )}
            {history.length > 0 ? (
              <LivePlotlyChart data={data} layout={layout} />
            ) : (
              !isError && (
                <Text role="status" c="dimmed">
                  {isFetching
                    ? "Checking spread and depth…"
                    : "Waiting for order-book depth."}
                </Text>
              )
            )}
          </>
        )}
      </Box>
      <Group mt="sm" c="dimmed">
        Visible depth from up to 100 levels per side. History collects across
        navigation while the terminal is open for the selected symbol. Resets on
        reload or symbol change.
      </Group>
    </Box>
  );
};

export default SpreadAndDepthCard;
