import { Exchange } from "binbot-charts";
import { calculateGridPnl } from "../features/gridLadders/gridLadders";
import type { GridLadder, GridLevel } from "../features/gridLadders/types";
import { dealColors } from "./charting";
import type { OrderLine } from "./charting/index.d";
import { MarketType } from "./enums";
import { roundDecimals } from "./math";
import { capitalizeFirst } from "./strings";

export const prominentBadgeClass = "";

export const formatLogEntry = (log: unknown): string => {
  if (typeof log === "string") {
    return log;
  }

  return JSON.stringify(log, null, 2) ?? String(log);
};

export const gridLevelColor = (level: GridLevel): string => {
  if (level.side === "buy") {
    return dealColors.base_order;
  }
  if (level.side === "sell") {
    return dealColors.safety_order;
  }
  return "#6c757d";
};

export const gridLevelLabel = (level: GridLevel): string => {
  if (level.side === "neutral") {
    return `L${level.level_index} neutral`;
  }
  return `L${level.level_index} ${capitalizeFirst(level.side)}`;
};

export const buildGridOrderLines = (ladder: GridLadder): OrderLine[] =>
  ladder.levels.flatMap((level) => {
    const quantity = `${level.contracts} contracts`;
    const lines: OrderLine[] = [
      {
        id: `${level.id}-entry`,
        text: gridLevelLabel(level),
        tooltip: [
          `Status: ${level.status}`,
          `Side: ${level.side}`,
          `Margin: ${level.margin_required} ${ladder.fiat}`,
        ],
        quantity,
        price: level.filled_entry_price || level.price,
        color: gridLevelColor(level),
        lineStyle: level.side === "neutral" ? 2 : undefined,
      },
    ];

    if (level.take_profit_price) {
      lines.push({
        id: `${level.id}-take-profit`,
        text: `L${level.level_index} TP`,
        tooltip: [
          `Status: ${level.status}`,
          `Entry: ${level.filled_entry_price || level.price}`,
          `Take profit: ${level.take_profit_price}`,
        ],
        quantity: `${level.filled_entry_qty || level.contracts} contracts`,
        price: level.take_profit_price,
        color: dealColors.take_profit,
        lineStyle: 2,
      });
    }

    return lines;
  });

export const chartSymbolForLadder = (ladder: GridLadder): string => {
  const exchange = ladder.exchange.toLowerCase();
  const marketType = ladder.market_type.toUpperCase();

  if (exchange !== Exchange.KUCOIN) {
    return ladder.symbol;
  }
  if (marketType === MarketType.FUTURES) {
    return ladder.symbol.endsWith("M") ? ladder.symbol : `${ladder.symbol}M`;
  }
  if (ladder.symbol.includes("-")) {
    return ladder.symbol;
  }

  const baseAsset = ladder.symbol.replace(ladder.fiat, "");
  return `${baseAsset}-${ladder.fiat}`;
};

export const isErrorStatus = (status?: string | null): boolean => {
  const value = status?.toLowerCase() ?? "";
  return ["error", "rejected", "expired", "range_broken"].some((errorStatus) =>
    value.includes(errorStatus),
  );
};

export const statusBadgeBg = (status?: string | null): "success" | "danger" =>
  isErrorStatus(status) ? "danger" : "success";

export const returnBadgeBg = (
  returnPct: number,
): "success" | "danger" | "secondary" => {
  if (returnPct > 0) {
    return "success";
  }
  if (returnPct < 0) {
    return "danger";
  }
  return "secondary";
};

export const calculateGridReturnPct = (ladder: GridLadder): number => {
  if (ladder.total_margin <= 0) {
    return 0;
  }

  return roundDecimals((calculateGridPnl(ladder) / ladder.total_margin) * 100);
};
