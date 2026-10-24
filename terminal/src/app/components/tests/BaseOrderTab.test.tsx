import "@testing-library/jest-dom";
import {
  fireEvent,
  render,
  screen as testingScreen,
  waitFor,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { Tab } from "react-bootstrap";
import { vi } from "vitest";

import { makeStore } from "../../store";
import { SymbolContext } from "../../hooks";
import BaseOrderTab from "../BaseOrderTab";
import {
  BotStatus,
  MarketType,
  QuoteAsset,
  TabsKeys,
} from "../../../utils/enums";
import { setBot } from "../../../features/bots/botSlice";
import {
  defaultRecoveryParams,
  singleBot,
  type Bot,
} from "../../../features/bots/botInitialState";

const settingsResponse = vi.hoisted(() => ({
  data: { fiat: "USDT", base_order_size: 123 },
  isLoading: false,
}));

vi.mock("../../../features/autotradeApiSlice", async () => {
  const actual = await vi.importActual("../../../features/autotradeApiSlice");

  return {
    ...actual,
    useGetSettingsQuery: vi.fn(() => settingsResponse),
  };
});

const symbolContextValue = {
  symbolsList: ["BTCUSDT", "ETHUSDT"],
  quoteAsset: "USDT",
  baseAsset: "BTC",
  futuresLeverage: 1,
  updateQuoteBaseState: vi.fn(),
  isLoading: false,
};

function renderLeverage(botOverrides: Partial<Bot> = {}) {
  const store = makeStore();
  store.dispatch(
    setBot({
      bot: {
        ...singleBot,
        pair: "XBTUSDTM",
        market_type: MarketType.FUTURES,
        ...botOverrides,
      },
    }),
  );
  render(
    <Provider store={store}>
      <SymbolContext.Provider
        value={{ ...symbolContextValue, futuresLeverage: 3 }}
      >
        <MemoryRouter initialEntries={["/bots/futures/new"]}>
          <Tab.Container activeKey={TabsKeys.MAIN}>
            <Tab.Content>
              <BaseOrderTab />
            </Tab.Content>
          </Tab.Container>
        </MemoryRouter>
      </SymbolContext.Provider>
    </Provider>,
  );
  return store;
}

describe("BaseOrderTab", () => {
  it("enables automatic recovery without exposing source metadata or changing order size", () => {
    const store = renderLeverage({ fiat_order_size: 25 });
    const recoveryToggle = testingScreen.getByRole("checkbox", {
      name: /^Recovery mode /,
    });

    fireEvent.click(recoveryToggle);

    expect(recoveryToggle).toBeChecked();
    expect(store.getState().bot.bot.recovery_params).toEqual(
      defaultRecoveryParams,
    );
    expect(store.getState().bot.bot.fiat_order_size).toBe(25);
    expect(testingScreen.queryByLabelText("Reversal path")).toBeNull();
    expect(testingScreen.queryByLabelText("Source contracts")).toBeNull();

    fireEvent.click(recoveryToggle);

    expect(recoveryToggle).not.toBeChecked();
    expect(store.getState().bot.bot.recovery_params).toBeNull();
    expect(store.getState().bot.bot.recovery_mode_id).toBeNull();
  });

  it("keeps recovery unavailable while dynamic position sizing is enabled", () => {
    const store = renderLeverage({ dynamic_position_sizing: true });
    const recoveryToggle = testingScreen.getByRole("checkbox", {
      name: /^Recovery mode /,
    });

    expect(recoveryToggle).toBeDisabled();
    fireEvent.click(recoveryToggle);
    expect(store.getState().bot.bot.recovery_params).toBeNull();
  });

  it("preserves the recovery role and parent link when displaying an existing child", () => {
    const recoveryParams = {
      ...defaultRecoveryParams,
      reversal_path: "recovery" as const,
      source_bot_id: "source-bot",
      source_contracts: 7,
    };
    const store = renderLeverage({ recovery_params: recoveryParams });

    expect(
      testingScreen.getByRole("checkbox", { name: /^Recovery mode / }),
    ).toBeChecked();
    expect(store.getState().bot.bot.recovery_params).toEqual(recoveryParams);
  });

  it("inherits symbol leverage for a new futures bot without submitting an override", () => {
    const store = renderLeverage();
    expect(
      testingScreen.getByRole("combobox", { name: "Leverage" }),
    ).toHaveValue("3");
    expect(store.getState().bot.bot.futures_leverage).toBeUndefined();
  });

  it("allows only 1x through 5x and stores the chosen leverage as a number", () => {
    const store = renderLeverage();
    const leverage = testingScreen.getByRole("combobox", { name: "Leverage" });
    expect(
      Array.from(leverage.querySelectorAll("option"), (option) => option.value),
    ).toEqual(["1", "2", "3", "4", "5"]);
    fireEvent.change(leverage, { target: { value: "5" } });
    expect(leverage).toHaveValue("5");
    expect(store.getState().bot.bot.futures_leverage).toBe(5);
  });

  it("shows the bot's saved leverage instead of the symbol default", () => {
    const store = renderLeverage({ futures_leverage: 4 });
    expect(
      testingScreen.getByRole("combobox", { name: "Leverage" }),
    ).toHaveValue("4");
    expect(store.getState().bot.bot.futures_leverage).toBe(4);
  });

  it.each([BotStatus.PENDING, BotStatus.ACTIVE, BotStatus.COMPLETED])(
    "locks leverage for a %s deal",
    (status) => {
      renderLeverage({ status, futures_leverage: 2 });
      expect(
        testingScreen.getByRole("combobox", { name: "Leverage" }),
      ).toBeDisabled();
    },
  );

  it("does not offer futures leverage for spot bots", () => {
    renderLeverage({ market_type: MarketType.SPOT });
    expect(
      testingScreen.queryByRole("combobox", { name: "Leverage" }),
    ).not.toBeInTheDocument();
  });

  it("applies the configured default fiat order size to a new bot", async () => {
    const store = makeStore();

    store.dispatch(
      setBot({
        bot: {
          ...singleBot,
          fiat: "USDC",
          fiat_order_size: 0,
          quote_asset: QuoteAsset.USDC,
        },
      }),
    );

    render(
      <Provider store={store}>
        <SymbolContext.Provider value={symbolContextValue}>
          <MemoryRouter initialEntries={["/bots/new"]}>
            <Tab.Container activeKey={TabsKeys.MAIN}>
              <Tab.Content>
                <BaseOrderTab />
              </Tab.Content>
            </Tab.Container>
          </MemoryRouter>
        </SymbolContext.Provider>
      </Provider>,
    );

    await waitFor(() => {
      expect(store.getState().bot.bot.fiat_order_size).toBe(123);
    });

    expect(store.getState().bot.bot.fiat).toBe("USDT");
    expect(store.getState().bot.bot.quote_asset).toBe("USDT");
  });
});
