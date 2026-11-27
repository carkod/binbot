import { Box, Group, Text, Title } from "@mantine/core";
import { useEffect, useMemo, useState } from "react";
import {
  useFuturesContractQuery,
  useFuturesTradesQuery,
} from "../../features/kucoinApiSlice";
import {
  summarizeRecentTrades,
  TRADES_POLL_INTERVAL_MS,
  TRADES_WINDOW_MS,
} from "../../features/kucoinTrades";
import LivePlotlyChart from "./LivePlotlyChart";

type SymbolTradesCardProps = {
  symbol: string;
  enabled: boolean;
};

const BUY_COLOR = "#198754";

const SELL_COLOR = "#dc3545";

const CHART_HEIGHT = 300;

const formatUsdt = (value: number) =>
  value.toLocaleString(undefined, { maximumFractionDigits: 0 });

const SymbolTradesCard = ({ symbol, enabled }: SymbolTradesCardProps) => {
  const skip = !enabled || !symbol;

  const {
    currentData: trades,
    isFetching,
    isError,
  } = useFuturesTradesQuery(symbol, {
    skip,
    pollingInterval: TRADES_POLL_INTERVAL_MS,
    refetchOnMountOrArgChange: true,
  });

  const { currentData: contract } = useFuturesContractQuery(symbol, { skip });

  const [now, setNow] = useState(Date.now);

  // Advance the window only when a poll returns different trades. RTK Query
  // keeps the same array when nothing changed, so a quiet contract stays still.
  useEffect(() => {
    setNow(Date.now());
  }, [trades]);

  // Slow tick so old trades still expire from a quiet contract.
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 30_000);

    return () => clearInterval(interval);
  }, []);

  const summary = useMemo(
    () =>
      trades && contract
        ? summarizeRecentTrades(trades, contract.multiplier, now)
        : undefined,
    [trades, contract, now],
  );

  const data = useMemo(() => {
    const points = summary?.trades ?? [];

    return ["buy", "sell"].map((side) => {
      const sidePoints = points.filter((trade) => trade.side === side);

      return {
        type: "scatter",
        mode: "lines+markers",
        line: { color: side === "buy" ? BUY_COLOR : SELL_COLOR, width: 1.5 },
        name: side === "buy" ? "Buy (taker)" : "Sell (taker)",
        x: sidePoints.map(({ timestamp }) => new Date(timestamp).toISOString()),
        y: sidePoints.map(({ price }) => price),
        ids: sidePoints.map(({ tradeId }) => tradeId),
        customdata: sidePoints.map(({ notional }) => notional),
        marker: {
          color: side === "buy" ? BUY_COLOR : SELL_COLOR,
          opacity: 0.75,
          size: sidePoints.map(({ notional }) =>
            Math.min(28, Math.max(6, Math.sqrt(notional) / 2)),
          ),
        },
        hovertemplate:
          "%{x|%H:%M:%S}<br>Price: %{y}<br>Notional: %{customdata:,.0f} USDT<extra></extra>",
      };
    });
  }, [summary]);

  const layout = useMemo(
    () => ({
      autosize: true,
      height: CHART_HEIGHT,
      showlegend: true,
      legend: { orientation: "h", y: 1.12 },
      margin: { t: 20, l: 80, r: 20, b: 50 },
      xaxis: {
        type: "date",
        range: [
          new Date(now - TRADES_WINDOW_MS).toISOString(),
          new Date(now).toISOString(),
        ],
        title: { text: "Last 5 minutes" },
      },
      yaxis: {
        autorange: true,
        title: { text: "Price (USDT)", standoff: 16 },
        automargin: true,
      },
    }),
    [now],
  );

  if (skip) return <Text>Enter a symbol</Text>;

  return (
    <Box>
      <Box mb="sm">
        <Title order={5}>Market trades</Title>
        <Text c="dimmed" mb={0}>
          Executed taker trades on the contract in the last 5 minutes. Marker
          size is USDT notional.
        </Text>
      </Box>
      {summary && (
        <Group mb="sm" gap="lg">
          <Text mb={0}>
            Buy: <strong>{formatUsdt(summary.buy)}</strong> USDT
          </Text>
          <Text mb={0}>
            Sell: <strong>{formatUsdt(summary.sell)}</strong> USDT
          </Text>
          <Text mb={0}>
            Delta: <strong>{formatUsdt(summary.delta)}</strong> USDT
          </Text>
          <Text mb={0} c="dimmed">
            {summary.trades.length} trades
          </Text>
        </Group>
      )}
      <Box mih={CHART_HEIGHT}>
        {!summary && isFetching && (
          <Text role="status">Loading {symbol} trades…</Text>
        )}
        {isError && (
          <Text role="alert">{symbol} trades could not be refreshed.</Text>
        )}
        {summary && !summary.trades.length && (
          <Text>No trades for {symbol} in the last 5 minutes.</Text>
        )}
        {!!summary?.trades.length && (
          <LivePlotlyChart data={data} layout={layout} />
        )}
      </Box>
      <Text c="dimmed" mt="sm" mb={0}>
        Smaller horizontal gaps mean trades happen more frequently.
        <br />
        Larger vertical changes between dots mean larger price moves. Check the
        y-axis to judge their size.
        <br />
        Positive delta: buyers eating sellers&apos; offers (buy pressure), with more
        USDT traded by buyers taking offers than sellers taking bids.
      </Text>
    </Box>
  );
};

export default SymbolTradesCard;
