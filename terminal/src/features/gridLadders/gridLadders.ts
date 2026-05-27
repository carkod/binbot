import { GridLadderStatus, type GridLadder } from "./types";

export { GridLadderStatus } from "./types";
export type { GridLevel, GridLadder } from "./types";

export type GridPositionSide = "long" | "short" | "flat";

export type GridPosition = {
  side: GridPositionSide;
  contracts: number;
  label: string;
};

export const isActiveGridLadder = (status: GridLadderStatus): boolean =>
  [
    GridLadderStatus.PENDING,
    GridLadderStatus.ACTIVE,
    GridLadderStatus.CLOSING,
  ].includes(status);

// Sum of per-level realized PnL from completed TP cycles.
// Useful for active ladders where ladder.realized_pnl is always 0 until close.
export const calculateLevelPnlSum = (ladder: GridLadder): number =>
  ladder.levels.reduce((a, l) => a + (l.realized_pnl ?? 0), 0);

export const calculateCloseAdjustmentPnl = (ladder: GridLadder): number => {
  if (isActiveGridLadder(ladder.status)) {
    return 0;
  }
  return ladder.realized_pnl - calculateLevelPnlSum(ladder);
};

export const calculateGridPnl = (ladder: GridLadder): number => {
  // Closed/errored ladders: backend writes the true realized_pnl at close.
  // Active/pending/closing: realized_pnl stays 0 by design — use per-level
  // TP-cycle profits plus the live position unrealized_pnl instead.
  if (!isActiveGridLadder(ladder.status)) {
    return ladder.realized_pnl;
  }
  return calculateLevelPnlSum(ladder) + ladder.unrealized_pnl;
};

export const resolveGridPosition = (ladder: GridLadder): GridPosition => {
  const openPositionStatuses = new Set(["filled", "take_profit_open"]);
  const isActive = isActiveGridLadder(ladder.status);

  const netContracts = ladder.levels.reduce((acc, level) => {
    if (level.side !== "buy" && level.side !== "sell") {
      return acc;
    }
    if (level.filled_entry_qty <= 0) {
      return acc;
    }
    if (isActive && !openPositionStatuses.has(level.status)) {
      return acc;
    }
    if (!isActive && level.status === "completed") {
      return acc;
    }

    const direction = level.side === "buy" ? 1 : -1;
    return acc + level.filled_entry_qty * direction;
  }, 0);

  const contracts = Math.abs(netContracts);
  if (contracts <= 0) {
    return {
      side: "flat",
      contracts: 0,
      label: isActive ? "No position" : "Closed",
    };
  }

  const side = netContracts > 0 ? "long" : "short";
  return {
    side,
    contracts,
    label: side,
  };
};

export const calculateFilledLevelCount = (ladder: GridLadder): number =>
  ladder.levels.filter((level) => level.filled_entry_qty > 0).length;

export const calculateOpenOrderCount = (ladder: GridLadder): number =>
  ladder.levels.filter(
    (level) => level.entry_order_id || level.take_profit_order_id,
  ).length;
