import { matchPath } from "react-router";

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

const matchNewRoutes = (pathname: string) => {
  const pathnames = ["/bots/futures/new/:symbol?", "/bots/new/:symbol?"];

  return pathnames.some((path) =>
    Boolean(matchPath({ path, end: true }, pathname)),
  );
};

export { listCssColors, matchNewRoutes };
