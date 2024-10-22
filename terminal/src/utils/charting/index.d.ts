export interface Order {
  order_id: string;
  deal_type: string;
  price: number;
  qty: number;
  timestamp: string;
}

export interface TimescaleMark {
  id: string;
  label: string;
  tooltip: string[];
  time: number;
  color: string;
}

export interface OrderLine {
  id: string;
  text: string;
  tooltip: string[];
  quantity: string;
  price: number;
  color: string;
  lineStyle?: number;
}

interface Deal {
  buy_price?: number;
  original_buy_price?: number;
  sell_price?: number;
  buy_total_qty?: number;
  trailling_stop_loss_price?: number;
  trailling_profit_price?: number;
  take_profit_price?: number;
}

interface SafetyOrder {
  name: string;
  status?: number;
  so_size: number;
  buy_price: number;
}
