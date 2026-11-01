import { useEffect, useMemo, useState, type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import { useAppDispatch, useAppSelector, useSymbolData } from "../hooks";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { roundDecimals } from "../../utils/math";
import { useImmer } from "use-immer";
import { updateOrderLines } from "../../utils/charting/index";
import { updateTimescaleMarks } from "../../utils/charting";
import TVChartContainer, { Exchange } from "binbot-charts";
import { type ResolutionString } from "../../../charting_library/charting_library";
import { type AppDispatch } from "../store";
import { type Bot } from "../../features/bots/botInitialState";
import { type PayloadActionCreator } from "@reduxjs/toolkit";
import { BotStatus, MarketType } from "../../utils/enums";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { capitalizeFirst } from "../../utils/strings";
import { selectBot } from "../../features/bots/botSlice";

const ChartContainer: FC<{
  bot: Bot;
  setCurrentPrice: PayloadActionCreator<number>;
  marketType: MarketType;
}> = ({ bot, setCurrentPrice, marketType }) => {
  const dispatch: AppDispatch = useAppDispatch();
  const { previewTrailingSettings } = useAppSelector(selectBot);
  const { quoteAsset } = useSymbolData();
  const [currentChartPrice, setCurrentChartPrice] = useImmer<number | null>(
    null,
  );
  const [exchangeSymbol, setExchangeSymbol] = useImmer<string>(bot.pair);
  const [botProfit, setBotProfit] = useState<number>(Number(0));
  const { data: autotradeSettings } = useGetSettingsQuery();
  const marketLabel = capitalizeFirst(marketType.toLowerCase());
  const exchangeState =
    autotradeSettings?.exchange_id?.toLowerCase() === "kucoin"
      ? Exchange.KUCOIN
      : Exchange.BINANCE;
  const orderLinePrice =
    currentChartPrice ??
    (bot.deal.current_price || bot.deal.opening_price || 0);
  const currentOrderLines = useMemo(
    () => updateOrderLines(bot, orderLinePrice, previewTrailingSettings),
    [bot, orderLinePrice, previewTrailingSettings],
  );

  const updatedPrice = (price: number) => {
    price = roundDecimals(price, 4);
    const roundedPrice = parseFloat(price.toString());
    if (currentChartPrice !== roundedPrice) {
      setCurrentChartPrice(roundedPrice);
    }
  };

  const handleInitialPrice = (price: number) => {
    if (!bot.deal.opening_price && bot.status !== BotStatus.ACTIVE) {
      setCurrentChartPrice(price);
    }
  };

  useEffect(() => {
    if (currentChartPrice === null) {
      return;
    }

    const nextBotProfit = computeSingleBotProfit(bot, currentChartPrice);
    setBotProfit((prev) => (prev !== nextBotProfit ? nextBotProfit : prev));

    if (bot.deal?.current_price !== currentChartPrice) {
      dispatch(setCurrentPrice(currentChartPrice));
    }
  }, [bot, currentChartPrice, dispatch, setCurrentPrice]);

  useEffect(() => {
    if (bot.id && bot.deal.opening_price > 0) {
      setBotProfit(computeSingleBotProfit(bot));
    }
    if (!bot?.pair) {
      return;
    }

    setExchangeSymbol((draft) => {
      if (exchangeState === Exchange.KUCOIN) {
        const baseAsset = bot.pair.replace(quoteAsset, "");
        let symbol = `${baseAsset}-${quoteAsset}`;
        if (bot.market_type === MarketType.FUTURES) {
          symbol = bot.pair;
        }
        if (symbol === draft) {
          return;
        }
        return symbol;
      }
    });
  }, [bot.pair, exchangeState, quoteAsset]);

  return (
    <Card
      style={{ display: "flex", flexDirection: "column", minHeight: "580px" }}
    >
      <Card.Header>
        <Row style={{ alignItems: "baseline" }}>
          <Col md="8">
            <Card.Title as="h3">
              {bot.pair}{" "}
              <Badge
                bg={
                  botProfit > 0
                    ? "success"
                    : botProfit < 0
                      ? "danger"
                      : "secondary"
                }
              >
                {botProfit ? botProfit + "% " : "0% "}
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
                {marketLabel}
              </Badge>
            </Card.Title>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {bot?.pair && (
          <TVChartContainer
            symbol={exchangeSymbol}
            // Take interval value from autotrade settings
            interval={"1h" as ResolutionString}
            timescaleMarks={updateTimescaleMarks(bot)}
            orderLines={currentOrderLines}
            onTick={(tick) => updatedPrice(parseFloat(tick.close))}
            getLatestBar={(bar) => handleInitialPrice(parseFloat(bar[3]))}
            exchange={exchangeState}
            style={{ minHeight: "100%", height: "600px", width: "100%" }}
          />
        )}
      </Card.Body>
    </Card>
  );
};

export default ChartContainer;
