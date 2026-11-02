import "@testing-library/jest-dom";
import {
  act,
  fireEvent,
  render,
  screen as testingScreen,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { Tab } from "react-bootstrap";

import { makeStore } from "../../store";
import TakeProfitTab from "../TakeProfitTab";
import { BotStatus, TabsKeys } from "../../../utils/enums";
import { setBot, setRecoveryParams } from "../../../features/bots/botSlice";
import {
  defaultRecoveryParams,
  singleBot,
  type Bot,
} from "../../../features/bots/botInitialState";

function renderTakeProfitTab(botOverrides: Partial<Bot> = {}) {
  const store = makeStore();
  store.dispatch(setBot({ bot: { ...singleBot, ...botOverrides } }));
  render(
    <Provider store={store}>
      <Tab.Container activeKey={TabsKeys.TAKEPROFIT}>
        <Tab.Content>
          <TakeProfitTab />
        </Tab.Content>
      </Tab.Container>
    </Provider>,
  );
  return store;
}

describe("TakeProfitTab trailing", () => {
  it.each(["source", "recovery"] as const)(
    "keeps the original trailing controls for a %s bot with recovery enabled",
    (reversal_path) => {
      const recoveryParams = { ...defaultRecoveryParams, reversal_path };
      const store = renderTakeProfitTab({
        id: "saved-bot",
        recovery_params: recoveryParams,
      });
      const toggle = testingScreen.getByRole("checkbox", {
        name: /^Trailing /,
      });

      expect(testingScreen.queryByText("Recovery trailing")).toBeNull();
      expect(toggle).not.toBeChecked();
      expect(testingScreen.queryByLabelText(/Trail profit at/)).toBeNull();
      fireEvent.click(toggle);

      expect(toggle).toBeChecked();
      expect(store.getState().bot.bot.trailing).toBe(true);
      fireEvent.change(testingScreen.getByLabelText(/Trail profit at/), {
        target: { value: "4.5" },
      });
      fireEvent.blur(testingScreen.getByLabelText(/Trail profit at/));
      fireEvent.change(testingScreen.getByLabelText("Trailing deviation"), {
        target: { value: "1.25" },
      });
      fireEvent.blur(testingScreen.getByLabelText("Trailing deviation"));

      expect(store.getState().bot.bot.trailing_profit).toBe(4.5);
      expect(store.getState().bot.bot.trailing_deviation).toBe(1.25);
      expect(store.getState().bot.bot.recovery_params).toEqual(recoveryParams);

      fireEvent.click(toggle);

      expect(store.getState().bot.bot.trailing).toBe(false);
      expect(store.getState().bot.bot.recovery_params).toEqual(recoveryParams);
      expect(testingScreen.queryByLabelText(/Trail profit at/)).toBeNull();
      expect(testingScreen.queryByLabelText("Trailing deviation")).toBeNull();
      expect(
        testingScreen.getByLabelText(/Take profit at/),
      ).toBeInTheDocument();
    },
  );

  it("keeps the normal trailing controls when recovery mode is off", () => {
    const store = renderTakeProfitTab();

    expect(
      testingScreen.queryByRole("checkbox", { name: /^Recovery trailing / }),
    ).toBeNull();
    fireEvent.click(
      testingScreen.getByRole("checkbox", { name: /^Trailing / }),
    );
    fireEvent.change(testingScreen.getByLabelText(/Trail profit at/), {
      target: { value: "0" },
    });
    fireEvent.blur(testingScreen.getByLabelText(/Trail profit at/));
    fireEvent.change(testingScreen.getByLabelText("Trailing deviation"), {
      target: { value: "0" },
    });
    fireEvent.blur(testingScreen.getByLabelText("Trailing deviation"));

    expect(store.getState().bot.bot.trailing).toBe(true);
    expect(store.getState().bot.bot.trailing_profit).toBe(0);
    expect(store.getState().bot.bot.trailing_deviation).toBe(0);
    expect(store.getState().bot.bot.recovery_params).toBeNull();
  });

  it("preserves trailing labels and settings when recovery mode changes in the base order tab", () => {
    const store = renderTakeProfitTab({
      trailing: true,
      trailing_profit: 4,
      trailing_deviation: 1.5,
    });

    act(() => {
      store.dispatch(setRecoveryParams({ ...defaultRecoveryParams }));
    });
    expect(
      testingScreen.getByRole("checkbox", { name: /^Trailing / }),
    ).toBeChecked();
    expect(testingScreen.queryByText("Recovery trailing")).toBeNull();
    expect(testingScreen.getByLabelText(/Trail profit at/)).toHaveValue(4);
    expect(testingScreen.getByLabelText("Trailing deviation")).toHaveValue(1.5);

    act(() => {
      store.dispatch(setRecoveryParams(null));
    });
    expect(
      testingScreen.getByRole("checkbox", { name: /^Trailing / }),
    ).toBeChecked();
    expect(store.getState().bot.bot.trailing_profit).toBe(4);
    expect(store.getState().bot.bot.trailing_deviation).toBe(1.5);
  });

  it("keeps both edits on an active bot and commits each value on blur", () => {
    const store = renderTakeProfitTab({
      id: "active-bot",
      status: BotStatus.ACTIVE,
      trailing: true,
      trailing_profit: 2.3,
      trailing_deviation: 0.63,
    });
    const profit = testingScreen.getByLabelText(/Trail profit at/);
    const deviation = testingScreen.getByLabelText("Trailing deviation");

    fireEvent.change(profit, { target: { value: "4.5" } });
    expect(store.getState().bot.bot.trailing_profit).toBe(2.3);
    fireEvent.blur(profit);
    expect(store.getState().bot.bot.trailing_profit).toBe(4.5);

    fireEvent.change(deviation, { target: { value: "1.25" } });
    expect(profit).toHaveValue(4.5);
    expect(store.getState().bot.bot.trailing_deviation).toBe(0.63);
    fireEvent.blur(deviation);

    expect(profit).toHaveValue(4.5);
    expect(deviation).toHaveValue(1.25);
    expect(store.getState().bot.bot).toMatchObject({
      trailing_profit: 4.5,
      trailing_deviation: 1.25,
    });
  });
});
