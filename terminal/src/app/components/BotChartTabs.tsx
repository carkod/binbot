import { useEffect, useId, type ComponentProps } from "react";
import { Badge, Card, Tab, Tabs } from "react-bootstrap";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { BotStatus, MarketType } from "../../utils/enums";
import { capitalizeFirst } from "../../utils/strings";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import ChartContainer from "./ChartContainer";
import OrderBookAnalysis from "./OrderBookAnalysis";

const resizeCharts = () => window.dispatchEvent(new Event("resize"));

const BotChartTabs = ({
  bot,
  setCurrentPrice,
  marketType,
}: ComponentProps<typeof ChartContainer>) => {
  const tabsId = useId();
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
      <Card>
        <Card.Body>
          <Card.Title as="h3" className="mb-0">
            {bot.pair}{" "}
            <Badge
              bg={profit > 0 ? "success" : profit < 0 ? "danger" : "secondary"}
            >
              {profit}%
            </Badge>{" "}
            <Badge
              bg={
                bot.status === BotStatus.ACTIVE
                  ? "success"
                  : bot.status === BotStatus.ERROR
                    ? "warning"
                    : bot.status === BotStatus.COMPLETED
                      ? "info"
                      : "secondary"
              }
            >
              {bot.status}
            </Badge>{" "}
            <Badge bg="info">{bot.position}</Badge>{" "}
            <Badge bg="dark" className="text-uppercase">
              {capitalizeFirst(marketType.toLowerCase())}
            </Badge>
          </Card.Title>
        </Card.Body>
      </Card>
      <Card>
        <Card.Body>
          <Tabs id={tabsId} defaultActiveKey="chart" className="mb-3">
            <Tab eventKey="chart" title="Chart" onEntered={resizeCharts}>
              <ChartContainer
                bot={bot}
                setCurrentPrice={setCurrentPrice}
                marketType={marketType}
              />
            </Tab>
            <Tab
              eventKey="analysis"
              title="Order book analysis"
              mountOnEnter
              unmountOnExit
            >
              {!supportsAnalysis ? (
                <p className="text-body-secondary">
                  Order book analysis is available for KuCoin futures bots.
                </p>
              ) : !pair ? (
                <p className="text-body-secondary">
                  Select a bot symbol to view order book analysis.
                </p>
              ) : symbol !== pair ? (
                <p role="status">Starting order book analysis…</p>
              ) : (
                <OrderBookAnalysis enabled showError />
              )}
            </Tab>
          </Tabs>
        </Card.Body>
      </Card>
    </>
  );
};

export default BotChartTabs;
