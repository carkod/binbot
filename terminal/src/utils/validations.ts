import { matchPath } from "react-router-dom";

const dataHeaders = [
  "Date",
  "Symbol",
  "Side",
  "Type",
  "Price",
  "Original Quantity",
  "Executed Quantity",
];

const listCssColors = [
  "#51cbce",
  "#fbc658",
  "#ef8157",
  "#E3E3E3",
  "#51bcda",
  "#c178c1",
  "#dcb285",
  "#f96332",
  "#6bd098",
];

const intervalOptions = [
  "1m",
  "3m",
  "5m",
  "15m",
  "30m",
  "1h",
  "2h",
  "4h",
  "6h",
  "8h",
  "12h",
  "1d",
  "3d",
  "1w",
];

const matchNewRoutes = (pathname: string) => {
  const pathnames = [
    "/bots/futures/new",
    "/bots/paper-trading/new",
    "/bots/new",
  ];
  return pathnames.some((path) => matchPath(pathname, path));
};

export { dataHeaders, intervalOptions, listCssColors, matchNewRoutes };
