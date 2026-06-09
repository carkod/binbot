import {
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { Tab } from "react-bootstrap";

import { makeStore } from "../../store";
import StopLossTab from "../StopLossTab";
import { BotType, TabsKeys } from "../../../utils/enums";

const renderStopLossTab = (botType: BotType = BotType.BOTS) => {
  const store = makeStore();
  const user = userEvent.setup();

  render(
    <Provider store={store}>
      <Tab.Container activeKey={TabsKeys.STOPLOSS}>
        <Tab.Content>
          <StopLossTab botType={botType} />
        </Tab.Content>
      </Tab.Container>
    </Provider>,
  );

  return { store, user };
};

describe("StopLossTab recovery params", () => {
  it("creates, edits, and clears recovery params with the recovery toggle", async () => {
    const { store, user } = renderStopLossTab();
    const recoveryToggle = testingScreen.getByRole("checkbox");

    await user.click(recoveryToggle);

    expect(store.getState().bot.bot.recovery_params).toEqual({
      reversal_path: "source",
      source_contracts: 0,
      source_loss_fiat: 0,
      stop_loss_pct: 0,
    });
    expect(testingScreen.getByLabelText("Reversal path")).not.toBeNull();

    fireEvent.change(testingScreen.getByLabelText("Reversal path"), {
      target: { value: "recovery" },
    });
    fireEvent.change(testingScreen.getByLabelText("Source contracts"), {
      target: { value: "7" },
    });
    fireEvent.change(testingScreen.getByLabelText("Source loss (USDC)"), {
      target: { value: "3.5" },
    });
    fireEvent.change(testingScreen.getByLabelText("Recovery stop loss"), {
      target: { value: "8" },
    });

    expect(store.getState().bot.bot.recovery_params).toMatchObject({
      reversal_path: "recovery",
      source_contracts: 7,
      source_loss_fiat: 3.5,
      stop_loss_pct: 8,
    });

    await user.click(recoveryToggle);

    expect(store.getState().bot.bot.recovery_mode_id).toBeNull();
    expect(store.getState().bot.bot.recovery_params).toBeNull();
    expect(testingScreen.queryByLabelText("Reversal path")).toBeNull();
  });

  it("does not show recovery controls for paper trading", () => {
    renderStopLossTab(BotType.PAPER_TRADING);

    expect(testingScreen.queryByText("Recovery mode")).toBeNull();
  });
});
