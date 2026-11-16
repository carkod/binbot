import { Badge, Box, Card, Tabs, Text, Title } from "@mantine/core";
import { useEffect, useId, useState, type ComponentProps } from "react";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { BotStatus, MarketType } from "../../utils/enums";
import { capitalizeFirst } from "../../utils/strings";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import ChartContainer from "./ChartContainer";
import OrderBookAnalysis from "./OrderBookAnalysis";
const BotChartTabs = ({
  bot,
  setCurrentPrice,
  marketType,
}: ComponentProps<typeof ChartContainer>) => {
  const tabsId = useId();
  const [activeTab, setActiveTab] = useState<string | null>("chart");
  useEffect(() => {
    const frame = requestAnimationFrame(() =>
      window.dispatchEvent(new Event("resize")),
    );
    return () => cancelAnimationFrame(frame);
  }, [activeTab]);
  const { data: settings } = useGetSettingsQuery();
  const { symbol, selectSymbol } = useMicrostructureData();
  const supportsAnalysis =
    marketType === MarketType.FUTURES &&
    settings?.exchange_id?.toLowerCase() === "kucoin";
  const pair = bot.pair.trim().toUpperCase();
  const profit = computeSingleBotProfit(bot);
  useEffect(() => {
    if (supportsAnalysis && pair) selectSymbol(pair);
  }, [supportsAnalysis, pair, selectSymbol]);
  return (
    <>
      <Title order={2} size="h4" mt={0} mb={24} c="dimmed">
        {bot.pair}{" "}
        <Badge
          color={profit > 0 ? "success" : profit < 0 ? "danger" : "secondary"}
          variant="light"
        >
          {profit}%
        </Badge>{" "}
        <Badge
          color={
            bot.status === BotStatus.ACTIVE
              ? "success"
              : bot.status === BotStatus.ERROR
                ? "warning"
                : bot.status === BotStatus.COMPLETED
                  ? "info"
                  : "secondary"
          }
          variant="light"
        >
          {bot.status}
        </Badge>{" "}
        <Badge color="info" variant="light">
          {bot.position}
        </Badge>{" "}
        <Badge color="dark" variant="light" tt="uppercase">
          {capitalizeFirst(marketType.toLowerCase())}
        </Badge>
      </Title>
      <Card mb="md">
        <Box>
          <Tabs
            id={tabsId}
            value={activeTab}
            onChange={setActiveTab}
            keepMountedMode="display-none"
            mb={16}
          >
            <Tabs.List>
              <Tabs.Tab value="chart">Chart</Tabs.Tab>
              <Tabs.Tab value="analysis">Order book analysis</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="chart" pt="md">
              <ChartContainer
                bot={bot}
                setCurrentPrice={setCurrentPrice}
                marketType={marketType}
              />
            </Tabs.Panel>
            <Tabs.Panel value="analysis" pt="md">
              <>
                {!supportsAnalysis ? (
                  <Text c="dimmed">
                    Order book analysis is available for KuCoin futures bots.
                  </Text>
                ) : !pair ? (
                  <Text c="dimmed">
                    Select a bot symbol to view order book analysis.
                  </Text>
                ) : symbol !== pair ? (
                  <Text role="status">Starting order book analysis…</Text>
                ) : (
                  <OrderBookAnalysis enabled showError />
                )}
              </>
            </Tabs.Panel>
          </Tabs>
        </Box>
      </Card>
    </>
  );
};
export default BotChartTabs;
