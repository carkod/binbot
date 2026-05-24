export enum GridLadderStatus {
  PENDING = "pending",
  ACTIVE = "active",
  CLOSING = "closing",
  CLOSED = "closed",
  RANGE_BROKEN = "range_broken",
  ERROR = "error",
}

export type GridLevel = {
  id: string;
  ladder_id: string;
  level_index: number;
  price: number;
  side: string;
  contracts: number;
  margin_required: number;
  status: string;
  entry_order_id?: string | null;
  take_profit_order_id?: string | null;
  filled_entry_price?: number | null;
  filled_entry_qty: number;
  take_profit_price?: number | null;
  realized_pnl: number;
  created_at: number;
  updated_at: number;
};

export type GridOrder = {
  id: string;
  ladder_id: string;
  level_id?: string | null;
  exchange_order_id: string;
  client_oid: string;
  order_role: string;
  status?: string | null;
  side?: string | null;
  price?: number | null;
  contracts: number;
  filled_qty: number;
  filled_price?: number | null;
  created_at: number;
  updated_at: number;
};

export type GridLadder = {
  id: string;
  symbol: string;
  fiat: string;
  exchange: string;
  market_type: string;
  algorithm_name: string;
  status: GridLadderStatus;
  range_low: number;
  range_high: number;
  grid_step: number;
  level_count: number;
  total_margin: number;
  reserved_margin: number;
  used_margin: number;
  realized_pnl: number;
  unrealized_pnl: number;
  breakout_low: number;
  breakout_high: number;
  created_at: number;
  updated_at: number;
  closed_at?: number | null;
  context: Record<string, unknown>;
  levels: GridLevel[];
  orders: GridOrder[];
};
