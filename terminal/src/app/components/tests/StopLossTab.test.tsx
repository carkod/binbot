import {
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { Tab } from "react-bootstrap";

import { makeStore } from "../../store";
import StopLossTab from "../StopLossTab";
import { TabsKeys } from "../../../utils/enums";
import { setBot } from "../../../features/bots/botSlice";
import {
  defaultRecoveryParams,
  singleBot,
  type Bot,
} from "../../../features/bots/botInitialState";

const renderStopLossTab = (botOverrides: Partial<Bot> = {}) => {
  const store = makeStore();
  store.dispatch(setBot({ bot: { ...singleBot, ...botOverrides } }));

  render(
    <Provider store={store}>
      <Tab.Container activeKey={TabsKeys.STOPLOSS}>
        <Tab.Content>
          <StopLossTab />
        </Tab.Content>
      </Tab.Container>
    </Provider>,
  );

  return { store };
};

describe("StopLossTab recovery params", () => {
  it("edits the recovery stop without exposing the recovery toggle or source metadata", () => {
    const { store } = renderStopLossTab({
      recovery_params: { ...defaultRecoveryParams },
    });
    expect(testingScreen.queryByRole("checkbox")).toBeNull();
    expect(testingScreen.queryByLabelText("Reversal path")).toBeNull();
    expect(testingScreen.queryByLabelText("Source contracts")).toBeNull();
    expect(testingScreen.queryByLabelText("Source loss (USDC)")).toBeNull();
    fireEvent.change(testingScreen.getByLabelText("Recovery stop loss"), {
      target: { value: "8" },
    });

    expect(store.getState().bot.bot.recovery_params).toMatchObject({
      reversal_path: "source",
      source_contracts: 0,
      source_loss_fiat: 0,
      stop_loss_pct: 8,
    });

    expect(store.getState().bot.bot.stop_loss).toBe(singleBot.stop_loss);
  });

  it("hides the recovery stop when recovery mode is off", () => {
    renderStopLossTab();
    expect(testingScreen.queryByLabelText("Recovery stop loss")).toBeNull();
  });

  it("preserves linked source metadata when editing a recovery stop", () => {
    const recoveryParams = {
      reversal_path: "recovery" as const,
      source_contracts: 7,
      source_loss_fiat: 3.5,
      source_bot_id: "source-bot",
      source_close_order_id: "source-stop",
      stop_loss_pct: 3,
    };
    const { store } = renderStopLossTab({ recovery_params: recoveryParams });

    fireEvent.change(testingScreen.getByLabelText("Recovery stop loss"), {
      target: { value: "4" },
    });

    expect(store.getState().bot.bot.recovery_params).toEqual({
      ...recoveryParams,
      stop_loss_pct: 4,
    });
    expect(testingScreen.queryByRole("combobox")).toBeNull();
    expect(testingScreen.queryByLabelText("Source contracts")).toBeNull();
    expect(testingScreen.queryByLabelText("Source loss (USDC)")).toBeNull();
  });
});
