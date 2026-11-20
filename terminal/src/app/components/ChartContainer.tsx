import { Text } from "@mantine/core";
import { type PayloadActionCreator } from "@reduxjs/toolkit";
import TVChartContainer, { Exchange } from "binbot-charts";
import { useEffect, useMemo, useRef, useState, type FC } from "react";
import { useImmer } from "use-immer";
import { type ResolutionString } from "../../../charting_library/charting_library";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { type Bot } from "../../features/bots/botInitialState";
import {
  focusOrderLine,
  selectBot,
  setField,
} from "../../features/bots/botSlice";
import { dealColors, updateTimescaleMarks } from "../../utils/charting";
import {
  canEditConditionalEntry,
  entryReferencePrice,
  fieldOrderLines,
  percentageFromOrderLine,
  type OrderLineField,
} from "../../utils/charting/editing";
import { updateOrderLines } from "../../utils/charting/index";
import { BotPosition, BotStatus, MarketType } from "../../utils/enums";
import { useAppDispatch, useAppSelector, useSymbolData } from "../hooks";
import { type AppDispatch } from "../store";

const ChartContainer: FC<{
  bot: Bot;
  setCurrentPrice: PayloadActionCreator<number>;
  marketType: MarketType;
  interval?: ResolutionString;
}> = ({ bot, setCurrentPrice, interval = "15" as ResolutionString }) => {
  const dispatch: AppDispatch = useAppDispatch();

  const {
    previewTrailingSettings,
    previewTrailingDeviationSettings,
    previewStopLossSettings,
    focusedOrderLine,
  } = useAppSelector(selectBot);

  const chartRef = useRef<HTMLDivElement>(null);

  const [dragError, setDragError] = useState("");

  const { quoteAsset } = useSymbolData();

  const [currentChartPrice, setCurrentChartPrice] = useImmer<number | null>(
    null,
  );

  const [exchangeSymbol, setExchangeSymbol] = useImmer<string>(bot.pair);

  const { data: autotradeSettings } = useGetSettingsQuery();

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
        previewTrailingDeviationSettings,
      ).map((line) => ({
        ...line,
        editable:
          bot.status !== BotStatus.COMPLETED &&
          Object.values(fieldOrderLines).includes(line.id) &&
          (line.id !== "base_order" || entryEditable),
      })),
    [
      bot,
      referencePrice,
      previewTrailingSettings,
      previewStopLossSettings,
      previewTrailingDeviationSettings,
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
        (entryEditable &&
          target.closest('[data-chart-field="entry_expires_at"]')) ||
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
  }, [dispatch, focusedOrderLine, entryEditable]);
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
    const field = (
      Object.entries(fieldOrderLines) as [OrderLineField, string][]
    ).find(([, lineId]) => lineId === id)?.[0];

    if (
      !field ||
      !currentOrderLines.some((line) => line.id === id && line.editable)
    )
      return;

    const reference =
      field === "trailing_deviation"
        ? currentOrderLines.find((line) => line.id === "trailing_profit")?.price
        : entryReferencePrice(bot, referencePrice);

    const value =
      field === "entry_price"
        ? Number.isFinite(price) && price > 0
          ? price
          : null
        : percentageFromOrderLine(field, price, reference, bot.position);

    if (value == null) {
      setDragError(
        field === "stop_loss"
          ? `For a ${bot.position} position, stop loss must be ${bot.position === BotPosition.SHORT ? "at or above" : "at or below"} the entry reference (${reference}). Dropped price: ${price}. Use a percentage below 100%.`
          : "Choose a price on the correct side of the reference, with a percentage below 100%.",
      );
      return;
    }
    setDragError("");
    dispatch(setField({ name: field, value }));
    document.getElementById(field)?.focus({ preventScroll: true });
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
    if (bot.deal?.current_price !== currentChartPrice) {
      dispatch(setCurrentPrice(currentChartPrice));
    }
  }, [bot, currentChartPrice, dispatch, setCurrentPrice]);
  useEffect(() => {
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
    <div
      ref={chartRef}
      style={{ display: "flex", flexDirection: "column", minHeight: "580px" }}
    >
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {focusedOrderLine === "stop_loss" &&
          bot.status !== BotStatus.COMPLETED && (
            <Text c="dimmed">
              Drag the red stop-loss line{" "}
              {bot.position === BotPosition.SHORT
                ? "at or above"
                : "at or below"}{" "}
              the entry reference ({entryReferencePrice(bot, referencePrice)}).
            </Text>
          )}
        {expiryMarker && (
          <Text c="dimmed">
            Drag the magenta expiry line to change the time. Pan the chart if it
            is offscreen. Press Escape to finish.
          </Text>
        )}
        {dragError && (
          <Text role="alert" c="danger.8">
            {dragError}
          </Text>
        )}
        {bot?.pair && (
          <TVChartContainer
            symbol={exchangeSymbol}
            interval={interval}
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
      </div>
    </div>
  );
};

export default ChartContainer;
