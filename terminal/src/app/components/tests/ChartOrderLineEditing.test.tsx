import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { Tab } from "react-bootstrap";
import { vi } from "vitest";
import { makeStore } from "../../store";
import { SymbolContext, useAppSelector } from "../../hooks";
import { singleBot, type Bot } from "../../../features/bots/botInitialState";
import {
  selectBot,
  setBot,
  setCurrentPrice,
} from "../../../features/bots/botSlice";
import {
  BotPosition,
  BotStatus,
  DealType,
  EntryMode,
  MarketType,
  TabsKeys,
} from "../../../utils/enums";
import ChartContainer from "../ChartContainer";
import StopLossTab from "../StopLossTab";
import TakeProfit from "../TakeProfitTab";
import BaseOrderTab from "../BaseOrderTab";
import { matchTsToTimescale } from "../../../utils/time";
const chart = vi.hoisted(() => ({ props: null as any }));
vi.mock("binbot-charts", () => ({
  default: (props: any) => {
    chart.props = props;
    return <div data-testid="chart" />;
  },
  Exchange: { KUCOIN: "kucoin", BINANCE: "binance" },
}));
vi.mock("../../../features/autotradeApiSlice", async () => ({
  ...(await vi.importActual("../../../features/autotradeApiSlice")),
  useGetSettingsQuery: () => ({
    data: { exchange_id: "kucoin", fiat: "USDT" },
    isLoading: false,
  }),
}));
function BotChart() {
  const { bot } = useAppSelector(selectBot);
  return (
    <ChartContainer
      bot={bot}
      setCurrentPrice={setCurrentPrice}
      marketType={MarketType.FUTURES}
    />
  );
}
function setup(tab: TabsKeys, overrides: Partial<Bot> = {}) {
  const store = makeStore();
  store.dispatch(
    setBot({
      bot: {
        ...singleBot,
        market_type: MarketType.FUTURES,
        pair: "XBTUSDTM",
        fiat_order_size: 100,
        trailing: true,
        trailing_profit: 6,
        trailing_deviation: 4,
        deal: { ...singleBot.deal, current_price: 100 },
        ...overrides,
      },
    }),
  );
  render(
    <Provider store={store}>
      <SymbolContext.Provider
        value={{
          symbolsList: [],
          quoteAsset: "USDT",
          baseAsset: "XBT",
          futuresLeverage: 1,
          updateQuoteBaseState: vi.fn(),
          isLoading: false,
        }}
      >
        <MemoryRouter>
          <Tab.Container activeKey={tab}>
            <Tab.Content>
              <StopLossTab />
              <TakeProfit />
              <BaseOrderTab />
            </Tab.Content>
          </Tab.Container>
          <BotChart />
          <button>Elsewhere</button>
        </MemoryRouter>
      </SymbolContext.Provider>
    </Provider>,
  );
  return store;
}
const editable = () =>
  chart.props.orderLines.filter((line) => line.editable).map((line) => line.id);
it.each([BotPosition.LONG, BotPosition.SHORT])(
  "updates the %s stop input and locks on leaving the chart",
  (position) => {
    const store = setup(TabsKeys.STOPLOSS, { position });
    fireEvent.focus(testingScreen.getByLabelText(/Stop loss/));
    expect(editable()).toEqual(["stop_loss"]);
    fireEvent.pointerDown(testingScreen.getByTestId("chart"));
    expect(editable()).toEqual(["stop_loss"]);
    act(() => {
      chart.props.onOrderLineMove(
        "stop_loss",
        position === BotPosition.LONG ? 95 : 105,
      );
    });
    expect(store.getState().bot.bot.stop_loss).toBe(5);
    expect(testingScreen.getByLabelText(/Stop loss/)).toHaveValue(5);
    fireEvent.pointerDown(
      testingScreen.getByRole("button", { name: "Elsewhere" }),
    );
    expect(editable()).toEqual([]);
  },
);
it("updates each trailing field from its own line", () => {
  const store = setup(TabsKeys.TAKEPROFIT);
  fireEvent.focus(testingScreen.getByLabelText(/Trail profit at/));
  expect(editable()).toEqual(["trailing_profit"]);
  act(() => {
    chart.props.onOrderLineMove("trailing_profit", 110);
  });
  expect(testingScreen.getByLabelText(/Trail profit at/)).toHaveValue(10);
  fireEvent.focus(testingScreen.getByLabelText("Trailing deviation"));
  expect(editable()).toEqual(["trailing_stop_loss"]);
  act(() => {
    chart.props.onOrderLineMove("trailing_stop_loss", 104.5);
  });
  expect(store.getState().bot.bot.trailing_deviation).toBe(5);
  expect(testingScreen.getByLabelText("Trailing deviation")).toHaveValue(5);
  expect(store.getState().bot.bot.trailing_profit).toBe(10);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(editable()).toEqual([]);
});
it("moves a conditional entry without changing expiry and refuses invalid stop drops", () => {
  const store = setup(TabsKeys.MAIN, {
    entry_mode: EntryMode.CONDITIONAL_LIMIT,
    entry_price: 100,
    entry_expires_at: 1800000000000,
  });
  fireEvent.focus(testingScreen.getByLabelText("Entry limit price"));
  expect(editable()).toEqual(["entry_price"]);
  act(() => {
    chart.props.onOrderLineMove("entry_price", 99);
  });
  expect(testingScreen.getByLabelText("Entry limit price")).toHaveValue(99);
  expect(store.getState().bot.bot.entry_expires_at).toBe(1800000000000);
  fireEvent.focus(testingScreen.getByLabelText(/Stop loss/));
  act(() => {
    chart.props.onOrderLineMove("stop_loss", 110);
  });
  expect(store.getState().bot.bot.stop_loss).toBe(3);
  expect(testingScreen.getByRole("alert")).toBeInTheDocument();
});
it.each([BotStatus.PENDING, BotStatus.ACTIVE, BotStatus.COMPLETED])(
  "keeps submitted or finished entry lines locked (%s)",
  (status) => {
    const expiresAt = Date.now() + 6 * 60 * 60 * 1000;
    const store = setup(TabsKeys.MAIN, {
      status,
      entry_mode: EntryMode.CONDITIONAL_LIMIT,
      entry_price: 100,
      entry_expires_at: expiresAt,
    });
    expect(testingScreen.getByLabelText("Entry limit price")).toBeDisabled();
    fireEvent.focus(testingScreen.getByLabelText("Entry limit price"));
    expect(editable()).toEqual([]);
    const expiry = testingScreen.getByLabelText("Entry expires at");
    expect(expiry).toBeDisabled();
    fireEvent.focus(expiry);
    expect(chart.props.timeMarker).toBeUndefined();
    act(() =>
      chart.props.onTimeMarkerMove(
        "conditional_entry_expiry",
        expiresAt / 1000 + 60,
      ),
    );
    expect(store.getState().bot.bot.entry_expires_at).toBe(expiresAt);
  },
);

it("updates the expiry input and mark while dragging only its focused handle", () => {
  const expiresAt = Math.ceil(Date.now() / 60000) * 60000 + 6 * 60 * 60 * 1000;
  const store = setup(TabsKeys.MAIN, {
    entry_mode: EntryMode.CONDITIONAL_LIMIT,
    entry_price: 100,
    entry_expires_at: expiresAt,
  });
  const input = testingScreen.getByLabelText(
    "Entry expires at",
  ) as HTMLInputElement;
  expect(chart.props.timeMarker).toBeUndefined();
  fireEvent.focus(input);
  expect(editable()).toEqual([]);
  expect(chart.props.timeMarker).toMatchObject({
    id: "conditional_entry_expiry",
    time: expiresAt / 1000,
  });
  fireEvent.pointerDown(testingScreen.getByTestId("chart"));
  for (const minutes of [15, 75]) {
    const time = expiresAt / 1000 + minutes * 60;
    act(() => chart.props.onTimeMarkerMove("conditional_entry_expiry", time));
    expect(store.getState().bot.bot.entry_expires_at).toBe(time * 1000);
    expect(new Date(input.value).getTime()).toBe(time * 1000);
    expect(chart.props.timeMarker.time).toBe(time);
    expect(
      chart.props.timescaleMarks.find(
        (mark) => mark.id === "conditional_entry_expiry",
      ).time,
    ).toBe(matchTsToTimescale(time * 1000));
  }
  fireEvent.focus(testingScreen.getByLabelText("Entry limit price"));
  expect(chart.props.timeMarker).toBeUndefined();
  fireEvent.focus(input);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(chart.props.timeMarker).toBeUndefined();
  fireEvent.focus(input);
  act(() => chart.props.onOrderLineEditCancel());
  expect(chart.props.timeMarker).toBeUndefined();
  fireEvent.focus(input);
  fireEvent.pointerDown(
    testingScreen.getByRole("button", { name: "Elsewhere" }),
  );
  expect(chart.props.timeMarker).toBeUndefined();
});

it("rejects past or invalid expiry drags and hides the handle in immediate mode", () => {
  const expiresAt = Date.now() + 6 * 60 * 60 * 1000;
  const store = setup(TabsKeys.MAIN, {
    entry_mode: EntryMode.CONDITIONAL_LIMIT,
    entry_price: 100,
    entry_expires_at: expiresAt,
  });
  fireEvent.focus(testingScreen.getByLabelText("Entry expires at"));
  for (const time of [Date.now() / 1000 - 60, NaN, Infinity, 1e30]) {
    act(() => chart.props.onTimeMarkerMove("conditional_entry_expiry", time));
    expect(store.getState().bot.bot.entry_expires_at).toBe(expiresAt);
  }
  expect(testingScreen.getByRole("alert")).toHaveTextContent("future");
  fireEvent.change(testingScreen.getByLabelText("Entry"), {
    target: { value: EntryMode.IMMEDIATE },
  });
  expect(chart.props.timeMarker).toBeUndefined();
  expect(chart.props.orderLines.some((line) => line.id === "entry_price")).toBe(
    false,
  );
  act(() =>
    chart.props.onTimeMarkerMove(
      "conditional_entry_expiry",
      expiresAt / 1000 + 60,
    ),
  );
  expect(store.getState().bot.bot.entry_expires_at).toBe(expiresAt);
  fireEvent.change(testingScreen.getByLabelText("Entry"), {
    target: { value: EntryMode.CONDITIONAL_LIMIT },
  });
  expect(chart.props.timeMarker).toBeUndefined();
});

it("keeps entry and expiry locked when an inactive bot already has an order", () => {
  setup(TabsKeys.MAIN, {
    entry_mode: EntryMode.CONDITIONAL_LIMIT,
    entry_price: 100,
    entry_expires_at: Date.now() + 6 * 60 * 60 * 1000,
    orders: [
      {
        order_id: "submitted",
        deal_type: DealType.BASE_ORDER,
        timestamp: Date.now(),
      },
    ],
  });
  expect(testingScreen.getByLabelText("Entry limit price")).toBeDisabled();
  expect(testingScreen.getByLabelText("Entry expires at")).toBeDisabled();
});

it("preserves low-price quote precision for conditional entry prefills", () => {
  const store = setup(TabsKeys.MAIN, {
    deal: { ...singleBot.deal, current_price: 0 },
  });
  act(() => chart.props.onTick({ close: "0.00001234" }));
  fireEvent.change(testingScreen.getByLabelText("Entry"), {
    target: { value: EntryMode.CONDITIONAL_LIMIT },
  });
  expect(store.getState().bot.bot.entry_price).toBe(0.00001234);
  expect(
    chart.props.orderLines.find((line) => line.id === "entry_price").price,
  ).toBe(0.00001234);
});

it.each([BotPosition.LONG, BotPosition.SHORT])(
  "keeps the %s stop at the dropped price when quotes arrive before and after refocusing",
  (position) => {
    const store = setup(TabsKeys.STOPLOSS, {
      position,
      deal: { ...singleBot.deal, current_price: 0 },
    });
    fireEvent.focus(testingScreen.getByLabelText(/Stop loss/));
    act(() => chart.props.onTick({ close: "100" }));
    act(() => chart.props.onTick({ close: "120" }));
    const price = position === BotPosition.LONG ? 95 : 105;
    act(() => chart.props.onOrderLineMove("stop_loss", price));
    expect(store.getState().bot.bot.stop_loss).toBe(5);
    expect(testingScreen.getByLabelText(/Stop loss/)).toHaveValue(5);
    act(() => chart.props.onTick({ close: "130" }));
    expect(
      chart.props.orderLines.find((line) => line.id === "stop_loss").price,
    ).toBe(price);
  },
);

it("keeps cleared stop-loss text out of chart calculations", () => {
  const store = setup(TabsKeys.STOPLOSS);
  fireEvent.change(testingScreen.getByLabelText(/Stop loss/), {
    target: { value: "" },
  });
  expect(store.getState().bot.bot.stop_loss).toBe(3);
  expect(
    chart.props.orderLines.every((line) => Number.isFinite(line.price)),
  ).toBe(true);
});
