import { GridLadderStatus, type GridLadder } from "./types";

export { GridLadderStatus } from "./types";
export type { GridLevel, GridLadder } from "./types";

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

export const calculateGridPnl = (ladder: GridLadder): number => {
  // Closed/errored ladders: backend writes the true realized_pnl at close.
  // Active/pending/closing: realized_pnl stays 0 by design — use per-level
  // TP-cycle profits plus the live position unrealized_pnl instead.
  if (!isActiveGridLadder(ladder.status)) {
    return ladder.realized_pnl;
  }
  return calculateLevelPnlSum(ladder) + ladder.unrealized_pnl;
};

export const calculateGridUtilization = (ladder: GridLadder): number => {
  if (ladder.total_margin <= 0) {
    return 0;
  }

  return (ladder.used_margin / ladder.total_margin) * 100;
};

export const calculateFilledLevelCount = (ladder: GridLadder): number =>
  ladder.levels.filter((level) => level.filled_entry_qty > 0).length;

export const calculateOpenOrderCount = (ladder: GridLadder): number =>
  ladder.levels.filter(
    (level) => level.entry_order_id || level.take_profit_order_id,
  ).length;
