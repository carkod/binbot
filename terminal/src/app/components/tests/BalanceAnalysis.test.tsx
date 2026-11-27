import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import {
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
  vi,
} from "vitest";
import { type Bot } from "../../../features/bots/botInitialState";
import { resetBot, setField } from "../../../features/bots/botSlice";
import { makeStore } from "../../store";
import { MarketType } from "../../../utils/enums";
import { act, render, screen as rtlScreen } from "../../../utils/render";

const useRiskBeta = vi.hoisted(() => vi.fn());

vi.mock("../../hooks/useRiskBeta", () => ({
  useRiskBeta,
}));

import BalanceAnalysis from "../BalanceAnalysis";

const accountData = {
  balances: { BTC: 1, USDT: 100 },
  fiat_available: 100,
  fiat_currency: "USDT",
  estimated_total_fiat: 200,
  total_deposit: 0,
};

function renderBalanceAnalysis(bot: Partial<Bot>) {
  const store = makeStore();

  store.dispatch(resetBot(bot));
  render(
    <Provider store={store}>
      <BalanceAnalysis accountData={accountData} />
    </Provider>,
  );
  return store;
}

describeBlock("BalanceAnalysis risk beta", () => {
  testCase("shows BTC beta calculated from 15-minute spot returns", () => {
    useRiskBeta.mockReturnValue({
      beta: 0.4567,
      isLoading: false,
    });

    renderBalanceAnalysis({ pair: "ETHUSDT", market_type: MarketType.SPOT });

    expectValue(
      rtlScreen.getByText("Symbol risk beta (BTC)"),
    ).toBeInTheDocument();
    expectValue(rtlScreen.getByText("0.46")).toBeInTheDocument();
    expectValue(useRiskBeta).toHaveBeenCalledWith("ETHUSDT", MarketType.SPOT);
  });

  testCase("shows beta for the selected futures symbol", () => {
    useRiskBeta.mockReturnValue({
      beta: -1.2345,
      isLoading: false,
    });

    renderBalanceAnalysis({
      pair: "HAEDALUSDTM",
      market_type: MarketType.FUTURES,
    });

    expectValue(rtlScreen.getByText("-1.23")).toBeInTheDocument();
    expectValue(useRiskBeta).toHaveBeenCalledWith(
      "HAEDALUSDTM",
      MarketType.FUTURES,
    );
  });

  testCase.each([
    { beta: null, isLoading: true, label: "Calculating..." },
    { beta: null, isLoading: false, label: "Unavailable" },
  ])(
    "shows $label while beta cannot be displayed",
    ({ beta, isLoading, label }) => {
      useRiskBeta.mockReturnValue({ beta, isLoading });

      renderBalanceAnalysis({
        pair: "HAEDALUSDTM",
        market_type: MarketType.FUTURES,
      });

      expectValue(rtlScreen.getByText(label)).toBeInTheDocument();
    },
  );

  testCase("follows bot replacement and symbol edits in botSlice", () => {
    useRiskBeta.mockReturnValue({ beta: 1, isLoading: false });

    const store = renderBalanceAnalysis({
      pair: "ETHUSDT",
      market_type: MarketType.SPOT,
    });

    expectValue(useRiskBeta).toHaveBeenLastCalledWith(
      "ETHUSDT",
      MarketType.SPOT,
    );

    act(() => {
      store.dispatch(
        resetBot({ pair: "HAEDALUSDTM", market_type: MarketType.FUTURES }),
      );
    });

    expectValue(useRiskBeta).toHaveBeenLastCalledWith(
      "HAEDALUSDTM",
      MarketType.FUTURES,
    );

    act(() => {
      store.dispatch(setField({ name: "pair", value: "ETHUSDTM" }));
    });

    expectValue(useRiskBeta).toHaveBeenLastCalledWith(
      "ETHUSDTM",
      MarketType.FUTURES,
    );
  });
});
