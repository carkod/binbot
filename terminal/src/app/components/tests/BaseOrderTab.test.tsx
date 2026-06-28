import { render, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { Tab } from "react-bootstrap";
import { vi } from "vitest";

import { makeStore } from "../../store";
import { SymbolContext } from "../../hooks";
import BaseOrderTab from "../BaseOrderTab";
import { BotType, TabsKeys } from "../../../utils/enums";
import { setBot } from "../../../features/bots/botSlice";
import { singleBot } from "../../../features/bots/botInitialState";

const settingsResponse = vi.hoisted(() => ({
  data: { fiat: "USDT", base_order_size: 123 },
  isLoading: false,
}));

vi.mock("../../../features/autotradeApiSlice", async () => {
  const actual = await vi.importActual(
    "../../../features/autotradeApiSlice",
  );

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

describe("BaseOrderTab", () => {
  it("applies default fiat order size to paper trading without mutating the live bot", async () => {
    const store = makeStore();

    store.dispatch(
      setBot({
        bot: {
          ...singleBot,
          fiat: "USDC",
          fiat_order_size: 777,
          quote_asset: "USDC",
        },
      }),
    );

    render(
      <Provider store={store}>
        <SymbolContext.Provider value={symbolContextValue}>
          <MemoryRouter initialEntries={["/paper-trading/new"]}>
            <Tab.Container activeKey={TabsKeys.MAIN}>
              <Tab.Content>
                <BaseOrderTab botType={BotType.PAPER_TRADING} />
              </Tab.Content>
            </Tab.Container>
          </MemoryRouter>
        </SymbolContext.Provider>
      </Provider>,
    );

    await waitFor(() => {
      expect(store.getState().paperTrading.paperTrading.fiat_order_size).toBe(
        123,
      );
    });

    expect(store.getState().paperTrading.paperTrading.fiat).toBe("USDT");
    expect(store.getState().paperTrading.paperTrading.quote_asset).toBe("USDT");
    expect(store.getState().bot.bot.fiat_order_size).toBe(777);
    expect(store.getState().bot.bot.fiat).toBe("USDC");
    expect(store.getState().bot.bot.quote_asset).toBe("USDC");
  });
});
