import { useEffect, useState, type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import { useAppDispatch, useAppSelector } from "../hooks";
import { selectBot, setCurrentPrice } from "../../features/bots/botSlice";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { roundDecimals } from "../../utils/math";
import { useImmer } from "use-immer";
import { updateOrderLines } from "../../utils/charting/index";
import { type OrderLine } from "../../utils/charting/index.d";
import { updateTimescaleMarks } from "../../utils/charting";
import TVChartContainer from "binbot-charts";
import { type ResolutionString } from "../../../charting_library/charting_library";
import { type AppDispatch } from "../store";
import { type Bot } from "../../features/bots/botInitialState";

const ChartContainer: FC = () => {
  const { bot } = useAppSelector(selectBot) as { bot: Bot };
  const dispatch: AppDispatch = useAppDispatch();
  const initialBotProfit = computeSingleBotProfit(bot);
  const [currentChartPrice, setCurrentChartPrice] = useImmer<number>(0);
  const [currentOrderLines, setCurrentOrderLines] = useImmer<OrderLine[]>([]);
  const [botProfit, setBotProfit] = useState<number>(Number(initialBotProfit));

  const updatedPrice = (price) => {
    price = roundDecimals(price, 4);
    if (currentChartPrice !== parseFloat(price)) {
      const newOrderLines = updateOrderLines(bot, price);
      setCurrentOrderLines(newOrderLines);
      setCurrentChartPrice(parseFloat(price));
    }
  };

  const handleInitialPrice = (price) => {
    if (!bot.deal.opening_price && bot.status !== "active") {
      setCurrentChartPrice(price);
    }
    const newOrderLines = updateOrderLines(bot, price);
    setCurrentOrderLines(newOrderLines);
  };

  useEffect(() => {
    if (initialBotProfit !== botProfit) {
      setBotProfit(initialBotProfit);
    }

    if (currentChartPrice !== 0) {
      const newOrderLines = updateOrderLines(bot, currentChartPrice);
      setCurrentOrderLines(newOrderLines);
      setBotProfit(computeSingleBotProfit(bot, currentChartPrice));
      if (bot.deal?.current_price !== currentChartPrice) {
        dispatch(setCurrentPrice(currentChartPrice));
      }
    }
  }, [
    currentChartPrice,
    bot,
    setCurrentOrderLines,
    setBotProfit,
    botProfit,
    dispatch,
    initialBotProfit,
  ]);

  return (
    <Card style={{ minHeight: "650px" }}>
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
                {botProfit ? botProfit + "%" : "0%"}
                {botProfit > 0 && botProfit - bot.commissions > 0 && (
                  <small className="fs-6 fw-light">
                    {roundDecimals(botProfit - bot.commissions) + "%"}
                  </small>
                )}
              </Badge>{" "}
              <Badge
                bg={
                  bot.status === "active"
                    ? "success"
                    : bot.status === "error"
                      ? "warning"
                      : bot.status === "completed"
                        ? "info"
                        : "secondary"
                }
              >
                {bot.status}
              </Badge>{" "}
              <Badge color="info">{bot.strategy}</Badge>
            </Card.Title>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {bot?.pair && (
          <TVChartContainer
            symbol={bot.pair}
            // Take interval value from autotrade settings
            interval={"1h" as ResolutionString}
            timescaleMarks={updateTimescaleMarks(bot)}
            orderLines={currentOrderLines}
            onTick={(tick) => updatedPrice(parseFloat(tick.close))}
            getLatestBar={(bar) => handleInitialPrice(parseFloat(bar[3]))}
          />
        )}
      </Card.Body>
    </Card>
  );
};

export default ChartContainer;
