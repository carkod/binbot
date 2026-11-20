import { Provider } from "react-redux";
import { vi } from "vitest";
import type { ResolutionString } from "../../../../charting_library/charting_library";
import { singleBot } from "../../../features/bots/botInitialState";
import {
  selectBot,
  setBot,
  setCurrentPrice,
  setField,
} from "../../../features/bots/botSlice";
import { BotStatus, MarketType } from "../../../utils/enums";
import { act, render, screen as rtlScreen } from "../../../utils/render";
import { SymbolContext, useAppSelector } from "../../hooks";
import { makeStore } from "../../store";
import ChartContainer from "../ChartContainer";

vi.mock("binbot-charts", () => ({
  default: ({
    orderLines,
    interval,
  }: {
    orderLines: { id: string; price: number }[];
    interval: string;
  }) => (
    <div data-testid="chart-lines" data-interval={interval}>
      {JSON.stringify(orderLines)}
    </div>
  ),
  Exchange: { KUCOIN: "kucoin", BINANCE: "binance" },
}));

vi.mock("../../../features/autotradeApiSlice", async () => ({
  ...(await vi.importActual("../../../features/autotradeApiSlice")),
  useGetSettingsQuery: () => ({ data: { exchange_id: "binance" } }),
}));

function BotChart({ interval }: { interval?: ResolutionString }) {
  const { bot } = useAppSelector(selectBot);

  return (
    <SymbolContext.Provider
      value={{
        symbolsList: [],
        quoteAsset: "USDC",
        baseAsset: "BTC",
        futuresLeverage: 1,
        updateQuoteBaseState: vi.fn(),
        isLoading: false,
      }}
    >
      <ChartContainer
        bot={bot}
        setCurrentPrice={setCurrentPrice}
        marketType={MarketType.SPOT}
        interval={interval}
      />
    </SymbolContext.Provider>
  );
}

it("updates active bot order lines on blur and when saved prices arrive", () => {
  const store = makeStore();

  const bot = {
    ...singleBot,
    id: "active-bot",
    pair: "BTCUSDC",
    candlestick_interval: "1h",
    status: BotStatus.ACTIVE,
    fiat_order_size: 25,
    trailing: true,
    trailing_profit: 3,
    trailing_deviation: 2,
    deal: {
      ...singleBot.deal!,
      opening_price: 100,
      current_price: 100,
      trailing_profit_price: 103,
      trailing_stop_loss_price: 101,
    },
  };

  store.dispatch(setBot({ bot }));
  render(
    <Provider store={store}>
      <BotChart />
    </Provider>,
  );

  const prices = () =>
    Object.fromEntries(
      JSON.parse(rtlScreen.getByTestId("chart-lines").textContent || "[]").map(
        (line: { id: string; price: number }) => [line.id, line.price],
      ),
    );

  expect(rtlScreen.getByTestId("chart-lines")).toHaveAttribute(
    "data-interval",
    "15",
  );
  expect(prices().trailing_profit).toBe(103);
  expect(prices().trailing_stop_loss).toBe(101);

  act(() => {
    store.dispatch(setField({ name: "trailing_profit", value: 5 }));
    store.dispatch(setField({ name: "trailing_deviation", value: 4 }));
  });
  expect(prices().trailing_profit).toBe(105);
  expect(prices().trailing_stop_loss).toBeCloseTo(100.8);

  act(() => {
    store.dispatch(
      setBot({
        bot: {
          ...bot,
          trailing_profit: 5,
          trailing_deviation: 4,
          deal: {
            ...bot.deal,
            trailing_profit_price: 105,
            trailing_stop_loss_price: 0,
          },
        },
      }),
    );
  });
  expect(prices().trailing_profit).toBe(105);
  expect(prices().trailing_stop_loss).toBeUndefined();
});

it("accepts a chart interval independently of bot settings", () => {
  const store = makeStore();

  store.dispatch(setBot({ bot: { ...singleBot, pair: "BTCUSDC" } }));
  render(
    <Provider store={store}>
      <BotChart interval={"5" as ResolutionString} />
    </Provider>,
  );

  expect(rtlScreen.getByTestId("chart-lines")).toHaveAttribute(
    "data-interval",
    "5",
  );
});
