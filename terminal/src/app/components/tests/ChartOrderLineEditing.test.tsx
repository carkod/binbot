import { Box, Tabs } from "@mantine/core";
import "@testing-library/jest-dom";
import userEvent from "@testing-library/user-event";
import moment from "moment";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
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
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
} from "../../../utils/render";
import { matchTsToTimescale } from "../../../utils/time";
import { SymbolContext, useAppSelector } from "../../hooks";
import { makeStore } from "../../store";
import BaseOrderTab from "../BaseOrderTab";
import ChartContainer from "../ChartContainer";
import StopLossTab from "../StopLossTab";
import TakeProfit from "../TakeProfitTab";
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
          <Tabs value={tab}>
            <Box>
              <StopLossTab />
              <TakeProfit />
              <BaseOrderTab />
            </Box>
          </Tabs>
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
it.each([
  [BotPosition.LONG, "stop_loss", "stop_loss", 95, 5],
  [BotPosition.SHORT, "stop_loss", "stop_loss", 105, 5],
  [BotPosition.LONG, "trailing_profit", "trailing_profit", 110, 10],
  [BotPosition.SHORT, "trailing_profit", "trailing_profit", 90, 10],
  [BotPosition.LONG, "trailing_stop_loss", "trailing_deviation", 100.7, 5],
  [BotPosition.SHORT, "trailing_stop_loss", "trailing_deviation", 98.7, 5],
  [BotPosition.LONG, "take_profit", "take_profit", 110, 10],
  [BotPosition.SHORT, "take_profit", "take_profit", 90, 10],
  [BotPosition.LONG, "base_order", "entry_price", 110, 110],
  [BotPosition.SHORT, "base_order", "entry_price", 110, 110],
] as const)(
  "updates %s %s directly without focusing its input",
  (position, lineId, field, price, expected) => {
    const store = setup(TabsKeys.MAIN, {
      position,
      trailing: field !== "take_profit",
      entry_mode: EntryMode.CONDITIONAL_LIMIT,
      entry_price: 100,
    });
    expect(store.getState().bot.focusedOrderLine).toBeNull();
    expect(editable()).toContain(lineId);
    act(() => chart.props.onOrderLineMove(lineId, price));
    expect(store.getState().bot.bot[field]).toBe(expected);
    expect(document.getElementById(field)).toHaveValue(expected);
    expect(
      chart.props.orderLines.find((line) => line.id === lineId)?.price,
    ).toBeCloseTo(price);
  },
);
it("updates the dropped line's field even when another input is focused", () => {
  const store = setup(TabsKeys.TAKEPROFIT);
  fireEvent.focus(testingScreen.getByLabelText(/Trail profit at/));
  act(() => chart.props.onOrderLineMove("stop_loss", 95));
  expect(store.getState().bot.bot.stop_loss).toBe(5);
  expect(store.getState().bot.bot.trailing_profit).toBe(6);
});
it.each([
  [BotPosition.LONG, 120, 114],
  [BotPosition.SHORT, 80, 84],
] as const)(
  "keeps the active %s trailing-profit level when dropping its deviation line",
  (position, profitPrice, stopPrice) => {
    const store = setup(TabsKeys.TAKEPROFIT, {
      position,
      status: BotStatus.ACTIVE,
      deal: {
        ...singleBot.deal,
        current_price: 110,
        opening_price: 100,
        trailing_profit_price: profitPrice,
        trailing_stop_loss_price: profitPrice,
      },
    });
    act(() => chart.props.onOrderLineMove("trailing_stop_loss", stopPrice));
    expect(store.getState().bot.bot.trailing_deviation).toBe(5);
    expect(
      chart.props.orderLines.find((line) => line.id === "trailing_profit")
        ?.price,
    ).toBe(profitPrice);
    expect(
      chart.props.orderLines.find((line) => line.id === "trailing_stop_loss")
        ?.price,
    ).toBeCloseTo(stopPrice);
  },
);
it("keeps completed bots and an immediate entry read-only", () => {
  const store = setup(TabsKeys.MAIN);
  expect(editable()).not.toContain("base_order");
  act(() => chart.props.onOrderLineMove("base_order", 110));
  expect(store.getState().bot.bot.entry_price).toBe(singleBot.entry_price);
  act(() => {
    store.dispatch(
      setBot({
        bot: { ...store.getState().bot.bot, status: BotStatus.COMPLETED },
      }),
    );
  });
  expect(editable()).toEqual([]);
  act(() => chart.props.onOrderLineMove("stop_loss", 95));
  expect(store.getState().bot.bot.stop_loss).toBe(3);
});
it.each([BotPosition.LONG, BotPosition.SHORT])(
  "updates the %s stop input without scrolling and remains draggable after leaving",
  (position) => {
    const store = setup(TabsKeys.STOPLOSS, { position });
    fireEvent.focus(testingScreen.getByLabelText(/Stop loss/));
    expect(editable()).toContain("stop_loss");
    fireEvent.pointerDown(testingScreen.getByTestId("chart"));
    expect(editable()).toContain("stop_loss");
    const input = testingScreen.getByLabelText(/Stop loss/);
    const focus = vi.spyOn(input, "focus");
    act(() => {
      chart.props.onOrderLineMove(
        "stop_loss",
        position === BotPosition.LONG ? 95 : 105,
      );
    });
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(input).toHaveFocus();
    focus.mockRestore();
    expect(store.getState().bot.bot.stop_loss).toBe(5);
    expect(testingScreen.getByLabelText(/Stop loss/)).toHaveValue(5);
    fireEvent.pointerDown(
      testingScreen.getByRole("button", { name: "Elsewhere" }),
    );
    expect(editable()).toContain("stop_loss");
  },
);
it("updates each trailing field from its own line", () => {
  const store = setup(TabsKeys.TAKEPROFIT);
  fireEvent.focus(testingScreen.getByLabelText(/Trail profit at/));
  expect(editable()).toContain("trailing_profit");
  act(() => {
    chart.props.onOrderLineMove("trailing_profit", 110);
  });
  expect(testingScreen.getByLabelText(/Trail profit at/)).toHaveValue(10);
  fireEvent.focus(testingScreen.getByLabelText("Trailing deviation"));
  expect(editable()).toContain("trailing_stop_loss");
  act(() => {
    chart.props.onOrderLineMove("trailing_stop_loss", 104.5);
  });
  expect(store.getState().bot.bot.trailing_deviation).toBe(5);
  expect(testingScreen.getByLabelText("Trailing deviation")).toHaveValue(5);
  expect(store.getState().bot.bot.trailing_profit).toBe(10);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(editable()).toContain("trailing_stop_loss");
});
it.each([BotPosition.LONG, BotPosition.SHORT])(
  "moves the single %s conditional entry line without changing expiry",
  (position) => {
    const store = setup(TabsKeys.MAIN, {
      position,
      entry_mode: EntryMode.CONDITIONAL_LIMIT,
      entry_price: 100,
      entry_expires_at: 1800000000000,
    });
    fireEvent.focus(testingScreen.getByLabelText("Entry limit price"));
    expect(editable()).toContain("base_order");
    expect(
      chart.props.orderLines.some(
        (line) => line.id === "entry_price" || line.id === "conditional_entry",
      ),
    ).toBe(false);
    expect(
      chart.props.orderLines
        .filter((line) => line.price === 100)
        .map((line) => line.id),
    ).toEqual(["base_order"]);
    act(() => {
      chart.props.onOrderLineMove("base_order", 99);
    });
    expect(testingScreen.getByLabelText("Entry limit price")).toHaveValue(99);
    expect(store.getState().bot.bot.entry_expires_at).toBe(1800000000000);
    expect(
      chart.props.orderLines.find((line) => line.id === "base_order").price,
    ).toBe(99);
    fireEvent.focus(testingScreen.getByLabelText(/Stop loss/));
    act(() => {
      chart.props.onOrderLineMove(
        "stop_loss",
        position === BotPosition.LONG ? 110 : 90,
      );
    });
    expect(store.getState().bot.bot.stop_loss).toBe(3);
    expect(testingScreen.getByRole("alert")).toBeInTheDocument();
  },
);
it.each([
  [BotPosition.LONG, "typing", 116.6, 111.936],
  [BotPosition.LONG, "dragging", 116.6, 111.936],
  [BotPosition.SHORT, "typing", 103.4, 107.536],
  [BotPosition.SHORT, "dragging", 103.4, 107.536],
] as const)(
  "recalculates %s trailing prices immediately when %s the conditional entry",
  (position, interaction, profitPrice, stopPrice) => {
    const store = setup(TabsKeys.MAIN, {
      position,
      entry_mode: EntryMode.CONDITIONAL_LIMIT,
      entry_price: 100,
    });
    const input = testingScreen.getByLabelText("Entry limit price");
    fireEvent.focus(input);
    if (interaction === "typing") {
      fireEvent.change(input, { target: { value: "110" } });
    } else {
      act(() => {
        chart.props.onOrderLineMove("base_order", 110);
      });
    }

    const expectTrailingPrices = () => {
      expect(
        chart.props.orderLines.find((line) => line.id === "trailing_profit")
          ?.price,
      ).toBeCloseTo(profitPrice);
      expect(
        chart.props.orderLines.find((line) => line.id === "trailing_stop_loss")
          ?.price,
      ).toBeCloseTo(stopPrice);
    };
    expect(input).toHaveValue(110);
    expect(store.getState().bot.bot.entry_price).toBe(110);
    expect(store.getState().bot.bot.trailing_profit).toBe(6);
    expect(store.getState().bot.bot.trailing_deviation).toBe(4);
    expectTrailingPrices();

    fireEvent.blur(input);
    fireEvent.pointerDown(
      testingScreen.getByRole("button", { name: "Elsewhere" }),
    );
    act(() => {
      chart.props.onTick({ close: "120" });
    });
    expectTrailingPrices();
  },
);
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
    expect(editable()).not.toContain("base_order");
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

it("updates the expiry picker and mark while dragging only its focused handle", async () => {
  const user = userEvent.setup();
  const expiresAt = Math.ceil(Date.now() / 60000) * 60000 + 6 * 60 * 60 * 1000;
  const store = setup(TabsKeys.MAIN, {
    entry_mode: EntryMode.CONDITIONAL_LIMIT,
    entry_price: 100,
    entry_expires_at: expiresAt,
  });
  const input = testingScreen.getByLabelText("Entry expires at");
  expect(chart.props.timeMarker).toBeUndefined();
  fireEvent.focus(input);
  expect(editable()).toContain("base_order");
  expect(chart.props.timeMarker).toMatchObject({
    id: "conditional_entry_expiry",
    time: expiresAt / 1000,
  });
  await user.click(input);
  await user.click(
    testingScreen.getByRole("spinbutton", { name: "Expiry hours" }),
  );
  expect(chart.props.timeMarker.time).toBe(expiresAt / 1000);
  await user.click(
    testingScreen.getByRole("button", { name: "Apply entry expiry" }),
  );
  fireEvent.pointerDown(testingScreen.getByTestId("chart"));
  for (const minutes of [15, 75]) {
    const time = expiresAt / 1000 + minutes * 60;
    act(() => chart.props.onTimeMarkerMove("conditional_entry_expiry", time));
    expect(store.getState().bot.bot.entry_expires_at).toBe(time * 1000);
    expect(input).toHaveTextContent(
      moment(time * 1000).format("DD/MM/YYYY HH:mm:ss"),
    );
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
    chart.props.orderLines.find((line) => line.id === "base_order").price,
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
