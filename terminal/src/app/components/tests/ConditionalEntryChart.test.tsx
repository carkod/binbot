import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
  waitFor,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { Tab } from "react-bootstrap";
import { vi } from "vitest";
import { makeStore } from "../../store";
import { SymbolContext, useAppSelector } from "../../hooks";
import { singleBot } from "../../../features/bots/botInitialState";
import {
  selectBot,
  setBot,
  setCurrentPrice,
} from "../../../features/bots/botSlice";
import {
  BotPosition,
  EntryMode,
  MarketType,
  TabsKeys,
} from "../../../utils/enums";
import BaseOrderTab from "../BaseOrderTab";
import ChartContainer from "../ChartContainer";

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

// Keep the installed binbot-charts component and TradingView wrapper real.
// Supply only the drawing API normally loaded over the network in its iframe.
async function readyChart(container: HTMLElement) {
  type Point = { time: number; price: number };
  const shapes = new Map<
    number,
    {
      text: string;
      points: Point[];
      editable: boolean;
      selectable: boolean;
      getPoints(): Point[];
      setPoints(points: Point[]): void;
      setUserEditEnabled(enabled: boolean): void;
      setSelectionEnabled(enabled: boolean): void;
      setProperties(properties: { text: string }): void;
    }
  >();
  const events = new Map<string, (...args: unknown[]) => void>();
  const chart = {
    refreshMarks: vi.fn(),
    createShape: async (
      point: Point,
      options: { text: string; lock: boolean; disableSelection: boolean },
    ) => {
      const id = shapes.size + 1;
      shapes.set(id, {
        text: options.text,
        points: [point],
        editable: !options.lock,
        selectable: !options.disableSelection,
        getPoints() {
          return this.points;
        },
        setPoints(points) {
          this.points = points;
        },
        setUserEditEnabled(enabled) {
          this.editable = enabled;
        },
        setSelectionEnabled(enabled) {
          this.selectable = enabled;
        },
        setProperties(properties) {
          this.text = properties.text;
        },
      });
      return id;
    },
    getShapeById: (id: number) => shapes.get(id),
    removeEntity: (id: number) => shapes.delete(id),
  };
  const iframe = container.querySelector("iframe")!;
  const frameWindow = iframe.contentWindow!;
  Object.assign(frameWindow, {
    widgetReady: (callback: () => void) => callback(),
    initializationFinished: vi.fn(),
    doWhenApiIsReady: (callback: () => void) => callback(),
    createShortcutAction: vi.fn(),
    tradingViewApi: {
      subscribe: (event: string, callback: (...args: unknown[]) => void) =>
        events.set(event, callback),
      unsubscribe: (event: string) => events.delete(event),
      activeChart: () => chart,
    },
  });
  // Keep the stub window available during cleanup, including older packages.
  Object.defineProperty(iframe, "contentWindow", { get: () => frameWindow });
  await act(async () => {
    frameWindow.dispatchEvent(
      new CustomEvent("innerWindowLoad", { detail: {} }),
    );
  });
  return {
    shapes,
    emit: (event: string, ...args: unknown[]) => events.get(event)?.(...args),
  };
}

beforeEach(() => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("about:blank");
});

afterEach(() => vi.restoreAllMocks());

it.each([BotPosition.LONG, BotPosition.SHORT])(
  "links the %s conditional input to the base drawing only while focused in conditional mode",
  async (position) => {
    const store = makeStore();
    store.dispatch(
      setBot({
        bot: {
          ...singleBot,
          market_type: MarketType.FUTURES,
          position,
          pair: "XBTUSDTM",
          fiat_order_size: 100,
          entry_mode: EntryMode.CONDITIONAL_LIMIT,
          entry_price: 100,
          deal: { ...singleBot.deal, current_price: 100 },
        },
      }),
    );
    const { container } = render(
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
            <Tab.Container activeKey={TabsKeys.MAIN}>
              <Tab.Content>
                <BaseOrderTab />
              </Tab.Content>
            </Tab.Container>
            <BotChart />
          </MemoryRouter>
        </SymbolContext.Provider>
      </Provider>,
    );
    const { shapes, emit } = await readyChart(container);
    const [entityId, entry] = [...shapes.entries()].find(([, shape]) =>
      shape.text.startsWith("Base"),
    )!;
    // Both entry modes share this one base drawing.
    expect(
      [...shapes.values()].filter((shape) => shape.points[0].price === 100),
    ).toEqual([entry]);
    expect(entry.editable).toBe(false);
    const input = testingScreen.getByLabelText("Entry limit price");
    fireEvent.focus(input);
    await waitFor(() => expect(entry.editable && entry.selectable).toBe(true));
    fireEvent.change(input, { target: { value: "98" } });
    await waitFor(() => expect(entry.points[0].price).toBe(98));
    await act(async () => {
      emit("mouse_down", {});
      entry.setPoints([{ time: 1800000000, price: 99 }]);
      emit("drawing_event", entityId, "points_changed");
      emit("mouse_up", {});
    });
    await waitFor(() => expect(input).toHaveValue(99));
    expect(store.getState().bot.bot.entry_price).toBe(99);
    expect(entry.points[0].price).toBe(99);
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(entry.editable).toBe(false));
    fireEvent.focus(input);
    await waitFor(() => expect(entry.editable).toBe(true));
    fireEvent.change(testingScreen.getByLabelText("Entry"), {
      target: { value: EntryMode.IMMEDIATE },
    });
    await waitFor(() => expect(entry.editable || entry.selectable).toBe(false));
    expect(store.getState().bot.bot.entry_price).toBeNull();
    expect(store.getState().bot.focusedOrderLine).toBeNull();
    expect(entry.points[0].price).toBe(100);
    expect(shapes.get(entityId)).toBe(entry);
    fireEvent.change(testingScreen.getByLabelText("Entry"), {
      target: { value: EntryMode.CONDITIONAL_LIMIT },
    });
    await waitFor(() => expect(entry.points[0].price).toBe(100));
    expect(entry.editable).toBe(false);
    fireEvent.focus(testingScreen.getByLabelText("Entry limit price"));
    await waitFor(() => expect(entry.editable).toBe(true));
  },
);
