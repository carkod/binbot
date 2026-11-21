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
