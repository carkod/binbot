import {
  fireEvent,
  render,
  screen as rtlScreen,
  waitFor,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";
import { makeStore } from "../../store";
import { setBot } from "../../../features/bots/botSlice";
import { singleBot } from "../../../features/bots/botInitialState";
import { BotStatus, MarketType } from "../../../utils/enums";
import BotDetailTabs from "../BotDetailTabs";

const { updateBot } = vi.hoisted(() => ({ updateBot: vi.fn() }));

vi.mock("../../../features/bots/botsApiSlice", async () => ({
  ...(await vi.importActual("../../../features/bots/botsApiSlice")),
  useEditBotMutation: () => [
    (args: { body: typeof singleBot; id: string }) => {
      updateBot(args);
      return { unwrap: async () => ({ bot: args.body }) };
    },
  ],
  useActivateBotMutation: () => [
    () => ({ unwrap: async () => ({}) }),
    { isLoading: false },
  ],
  useDeactivateBotMutation: () => [vi.fn(), { isLoading: false }],
  useCreateBotMutation: () => [vi.fn()],
}));

vi.mock("../BaseOrderTab", () => ({ default: () => null }));
vi.mock("../StopLossTab", () => ({ default: () => null }));

it("submits both trailing edits after their fields lose focus", async () => {
  const store = makeStore();
  store.dispatch(
    setBot({
      bot: {
        ...singleBot,
        id: "active-bot",
        status: BotStatus.ACTIVE,
        trailing: true,
        trailing_profit: 2.3,
        trailing_deviation: 0.63,
      },
    }),
  );
  render(
    <Provider store={store}>
      <MemoryRouter initialEntries={["/bots/futures/edit/active-bot"]}>
        <Routes>
          <Route
            path="/bots/futures/edit/:id"
            element={<BotDetailTabs marketType={MarketType.FUTURES} />}
          />
        </Routes>
      </MemoryRouter>
    </Provider>,
  );

  fireEvent.click(rtlScreen.getByRole("tab", { name: "Take Profit" }));
  const profit = rtlScreen.getByLabelText(/Trail profit at/);
  const deviation = rtlScreen.getByLabelText("Trailing deviation");
  fireEvent.change(profit, { target: { value: "4.5" } });
  fireEvent.blur(profit);
  fireEvent.change(deviation, { target: { value: "1.25" } });
  fireEvent.blur(deviation);
  fireEvent.click(rtlScreen.getByRole("button", { name: "Update deal" }));

  await waitFor(() => {
    expect(updateBot).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "active-bot",
        body: expect.objectContaining({
          trailing_profit: 4.5,
          trailing_deviation: 1.25,
        }),
      }),
    );
  });
});
