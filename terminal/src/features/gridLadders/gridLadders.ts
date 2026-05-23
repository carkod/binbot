import { GridLadderStatus, type GridLadder } from "./types";

export { GridLadderStatus } from "./types";
export type { GridLevel, GridLadder } from "./types";

export const isActiveGridLadder = (status: GridLadderStatus): boolean =>
  [GridLadderStatus.PENDING, GridLadderStatus.ACTIVE, GridLadderStatus.CLOSING].includes(status);

export const calculateGridPnl = (ladder: GridLadder): number =>
  ladder.realized_pnl + ladder.unrealized_pnl;

export const calculateGridUtilization = (ladder: GridLadder): number => {
  if (ladder.total_margin <= 0) {
    return 0;
  }

  return (ladder.used_margin / ladder.total_margin) * 100;
};

export const calculateFilledLevelCount = (ladder: GridLadder): number =>
  ladder.levels.filter((level) => level.filled_entry_qty > 0).length;

export const calculateOpenOrderCount = (ladder: GridLadder): number =>
  ladder.levels.filter((level) => level.entry_order_id || level.take_profit_order_id).length;
