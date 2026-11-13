import { useEffect, useMemo, useRef, useState, type FC } from "react";
import { Badge, Card, Col, Row } from "react-bootstrap";
import { useAppDispatch, useAppSelector, useSymbolData } from "../hooks";
import { computeSingleBotProfit } from "../../features/bots/profits";
import { useImmer } from "use-immer";
import { updateOrderLines } from "../../utils/charting/index";
import { dealColors, updateTimescaleMarks } from "../../utils/charting";
import TVChartContainer, { Exchange } from "binbot-charts";
import { type ResolutionString } from "../../../charting_library/charting_library";
import { type AppDispatch } from "../store";
import { type Bot } from "../../features/bots/botInitialState";
import { type PayloadActionCreator } from "@reduxjs/toolkit";
import { BotPosition, BotStatus, MarketType } from "../../utils/enums";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { capitalizeFirst } from "../../utils/strings";
import {
  selectBot,
  focusOrderLine,
  setField,
} from "../../features/bots/botSlice";

import {
  canEditConditionalEntry,
  entryReferencePrice,
  fieldOrderLines,
  percentageFromOrderLine,
} from "../../utils/charting/editing";

const ChartContainer: FC<{
  bot: Bot;
  setCurrentPrice: PayloadActionCreator<number>;
  marketType: MarketType;
}> = ({ bot, setCurrentPrice, marketType }) => {
  const dispatch: AppDispatch = useAppDispatch();
  const { previewTrailingSettings, previewStopLossSettings, focusedOrderLine } =
    useAppSelector(selectBot);
  const chartRef = useRef<HTMLDivElement>(null);
  const [dragError, setDragError] = useState("");
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
  // Freeze the quote reference while an input is selected so live ticks cannot
  // change the percentage represented by a dragged price.
  const focusKey = `${bot.id}:${bot.pair}:${bot.position}:${bot.entry_mode}:${focusedOrderLine}`;
  const [focusQuote, setFocusQuote] = useState({
    key: focusKey,
    price: orderLinePrice,
  });
  // Capture the first available quote even when focus preceded chart loading.
  // Refocusing the same field after a drop must keep the original reference.
  if (
    focusQuote.key !== focusKey ||
    (focusedOrderLine && focusQuote.price <= 0 && orderLinePrice > 0)
  ) {
    setFocusQuote({ key: focusKey, price: orderLinePrice });
  }
  const referencePrice =
    focusedOrderLine && focusQuote.price > 0
      ? focusQuote.price
      : orderLinePrice;
  const entryEditable = canEditConditionalEntry(bot);
  const expiryMarker =
    entryEditable &&
    focusedOrderLine === "entry_expires_at" &&
    Number.isFinite(bot.entry_expires_at) &&
    bot.entry_expires_at > 0
      ? {
          id: "conditional_entry_expiry",
          time: bot.entry_expires_at / 1000,
          text: "Conditional entry expires",
          color: dealColors.entry_price,
        }
      : undefined;
  const currentOrderLines = useMemo(
    () =>
      updateOrderLines(
        bot,
        referencePrice,
        previewTrailingSettings,
        previewStopLossSettings,
      ).map((line) => ({
        ...line,
        editable:
          bot.status !== BotStatus.COMPLETED &&
          focusedOrderLine != null &&
          focusedOrderLine !== "entry_expires_at" &&
          line.id === fieldOrderLines[focusedOrderLine] &&
          (focusedOrderLine !== "entry_price" || entryEditable),
      })),
    [
      bot,
      referencePrice,
      previewTrailingSettings,
      previewStopLossSettings,
      focusedOrderLine,
      entryEditable,
    ],
  );
  const timescaleMarks = useMemo(
    () => updateTimescaleMarks(bot),
    [
      bot.orders,
      bot.entry_mode,
      bot.entry_price,
      bot.created_at,
      bot.entry_expires_at,
      bot.fiat,
      bot.quote_asset,
      bot.position,
      bot.status,
    ],
  );

  useEffect(() => {
    const leave = (event: Event) => {
      const target = event.target as HTMLElement;
      if (
        chartRef.current?.contains(target) ||
        (target instanceof HTMLInputElement &&
          (target.id in fieldOrderLines || target.id === "entry_expires_at") &&
          !target.disabled)
      )
        return;
      dispatch(focusOrderLine(null));
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") dispatch(focusOrderLine(null));
    };
    document.addEventListener("focusin", leave);
    document.addEventListener("pointerdown", leave);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("focusin", leave);
      document.removeEventListener("pointerdown", leave);
      document.removeEventListener("keydown", escape);
    };
  }, [dispatch, focusedOrderLine]);

  useEffect(() => {
    setDragError("");
  }, [focusKey]);

  useEffect(() => {
    if (
      !entryEditable &&
      (focusedOrderLine === "entry_price" ||
        focusedOrderLine === "entry_expires_at")
    ) {
      dispatch(focusOrderLine(null));
    }
  }, [entryEditable, focusedOrderLine, dispatch]);

  useEffect(
    () => () => {
      dispatch(focusOrderLine(null));
    },
    [dispatch],
  );

  const handleOrderLineMove = (id: string, price: number) => {
    if (
      !focusedOrderLine ||
      focusedOrderLine === "entry_expires_at" ||
      !currentOrderLines.some((line) => line.id === id && line.editable)
    )
      return;
    const reference =
      focusedOrderLine === "trailing_deviation"
        ? currentOrderLines.find((line) => line.id === "trailing_profit")?.price
        : entryReferencePrice(bot, referencePrice);
    const value =
      focusedOrderLine === "entry_price"
        ? Number.isFinite(price) && price > 0
          ? price
          : null
        : percentageFromOrderLine(
            focusedOrderLine,
            price,
            reference,
            bot.position,
          );
    if (value == null) {
      setDragError(
        focusedOrderLine === "stop_loss"
          ? `For a ${bot.position} position, stop loss must be ${bot.position === BotPosition.SHORT ? "at or above" : "at or below"} the entry reference (${reference}). Dropped price: ${price}. Use a percentage below 100%.`
          : "Choose a price on the correct side of the reference, with a percentage below 100%.",
      );
      return;
    }
    setDragError("");
    dispatch(setField({ name: focusedOrderLine, value }));
    document.getElementById(focusedOrderLine)?.focus();
  };

  const handleTimeMarkerMove = (id: string, time: number) => {
    if (!expiryMarker || id !== expiryMarker.id || !Number.isFinite(time))
      return;
    const expiresAt = time * 1000;
    if (
      !Number.isFinite(new Date(expiresAt).getTime()) ||
      expiresAt <= Date.now()
    ) {
      setDragError("Choose an entry expiry in the future.");
      return;
    }
    setDragError("");
    dispatch(setField({ name: "entry_expires_at", value: expiresAt }));
  };

  const updatedPrice = (price: number) => {
    // Keep exchange precision for entry prefills and dragged percentages.
    if (Number.isFinite(price) && price > 0 && currentChartPrice !== price) {
      setCurrentChartPrice(price);
    }
  };

  const handleInitialPrice = (price: number) => {
    if (
      !bot.deal.opening_price &&
      bot.status !== BotStatus.ACTIVE &&
      Number.isFinite(price) &&
      price > 0
    ) {
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
      ref={chartRef}
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
        {focusedOrderLine === "stop_loss" &&
          bot.status !== BotStatus.COMPLETED && (
            <p className="text-muted">
              Drag the red stop-loss line{" "}
              {bot.position === BotPosition.SHORT
                ? "at or above"
                : "at or below"}{" "}
              the entry reference ({entryReferencePrice(bot, referencePrice)}).
            </p>
          )}
        {expiryMarker && (
          <p className="text-muted">
            Drag the magenta expiry line to change the time. Pan the chart if it
            is offscreen. Press Escape to finish.
          </p>
        )}
        {dragError && (
          <p role="alert" className="text-danger">
            {dragError}
          </p>
        )}
        {bot?.pair && (
          <TVChartContainer
            symbol={exchangeSymbol}
            interval={"60" as ResolutionString}
            timescaleMarks={timescaleMarks}
            timeMarker={expiryMarker}
            onTimeMarkerMove={handleTimeMarkerMove}
            onOrderLineMove={handleOrderLineMove}
            onOrderLineEditCancel={() => dispatch(focusOrderLine(null))}
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
