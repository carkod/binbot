import React, { useEffect, useState, type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import { useAppDispatch, useSymbolData } from "../hooks";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { roundDecimals } from "../../utils/math";
import { useImmer } from "use-immer";
import { updateOrderLines } from "../../utils/charting/index";
import { type OrderLine } from "../../utils/charting/index.d";
import { updateTimescaleMarks } from "../../utils/charting";
import TVChartContainer, { Exchange } from "binbot-charts";
import { type ResolutionString } from "../../../charting_library/charting_library";
import { type AppDispatch } from "../store";
import { type Bot } from "../../features/bots/botInitialState";
import { type PayloadActionCreator } from "@reduxjs/toolkit";
import { BotStatus, MarketType } from "../../utils/enums";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { capitalizeFirst } from "../../utils/strings";

const ChartContainer: FC<{
  bot: Bot;
  setCurrentPrice: PayloadActionCreator<number>;
  marketType: MarketType;
}> = ({ bot, setCurrentPrice, marketType }) => {
  const dispatch: AppDispatch = useAppDispatch();
  const { quoteAsset } = useSymbolData();
  const [currentChartPrice, setCurrentChartPrice] = useImmer<number | null>(
    null,
  );
  const [currentOrderLines, setCurrentOrderLines] = useImmer<OrderLine[]>([]);
  const [exchangeSymbol, setExchangeSymbol] = useImmer<string>(bot.pair);
  const [botProfit, setBotProfit] = useState<number>(Number(0));
  const { data: autotradeSettings } = useGetSettingsQuery();
  const marketLabel = capitalizeFirst(marketType.toLowerCase());
  const exchangeState =
    autotradeSettings?.exchange_id?.toLowerCase() === "kucoin"
      ? Exchange.KUCOIN
      : Exchange.BINANCE;

  const updatedPrice = (price: number) => {
    price = roundDecimals(price, 4);
    const roundedPrice = parseFloat(price.toString());
    if (currentChartPrice !== roundedPrice) {
      const newOrderLines = updateOrderLines(bot, roundedPrice);
      setCurrentOrderLines(newOrderLines);
      setCurrentChartPrice(roundedPrice);
    }
  };

  const handleInitialPrice = (price: number) => {
    if (!bot.deal.opening_price && bot.status !== BotStatus.ACTIVE) {
      setCurrentChartPrice(price);
    }
    const newOrderLines = updateOrderLines(bot, price);
    setCurrentOrderLines(newOrderLines);
  };

  useEffect(() => {
    if (currentChartPrice === null) {
      return;
    }

    const newOrderLines = updateOrderLines(bot, currentChartPrice);
    const hasDifferentOrderLines =
      JSON.stringify(newOrderLines) !== JSON.stringify(currentOrderLines);

    if (hasDifferentOrderLines) {
      setCurrentOrderLines(newOrderLines);
    }

    const nextBotProfit = computeSingleBotProfit(bot, currentChartPrice);
    setBotProfit((prev) => (prev !== nextBotProfit ? nextBotProfit : prev));

    if (bot.deal?.current_price !== currentChartPrice) {
      dispatch(setCurrentPrice(currentChartPrice));
    }
  }, [bot, currentChartPrice, currentOrderLines, dispatch, setCurrentPrice]);

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
              <Badge bg="info">{bot.strategy}</Badge>{" "}
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
