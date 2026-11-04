import { fireEvent, render } from "@testing-library/react";

import { singleBot } from "../../../features/bots/botInitialState";
import BotInfo from "../BotInfo";

describe("BotInfo", () => {
  it("hides the internal conditional close order from deal information", () => {
    const deal = {
      ...singleBot.deal!,
      conditional_close_order: { order_id: "internal-close" },
    };
    const view = render(<BotInfo bot={{ ...singleBot, deal, orders: [{}] }} />);

    fireEvent.click(view.getByRole("tab", { name: "Deal information" }));
    expect(view.queryByText("conditional_close_order")).toBeNull();
    expect(view.queryByText("internal-close")).toBeNull();
    expect(view.getByText("opening_price")).toBeTruthy();
  });

  it("displays the current position quantity in deal information", () => {
    const view = render(
      <BotInfo
        bot={{
          ...singleBot,
          deal: {
            ...singleBot.deal!,
            opening_qty: 4522,
            current_position_qty: 922,
          },
          orders: [{}],
        }}
      />,
    );

    fireEvent.click(view.getByRole("tab", { name: "Deal information" }));
    expect(view.getByText("current_position_qty")).toBeTruthy();
    expect(view.getByText("922")).toBeTruthy();
  });

  it("shows orders first and collapses both tabs together", () => {
    const view = render(
      <BotInfo
        bot={{
          ...singleBot,
          orders: [
            {
              order_id: "order-1",
              timestamp: "1700000000000",
              deal_type: "base_order",
              order_type: "limit",
              price: 100,
              qty: "2",
              status: "FILLED",
              order_side: "buy",
            },
          ],
        }}
      />,
    );

    expect(
      view
        .getByRole("tab", { name: "Orders information" })
        .getAttribute("aria-selected"),
    ).toBe("true");
    expect(view.getByText("order-1")).toBeTruthy();
    expect(view.queryByText("opening_price")).toBeNull();

    fireEvent.click(view.getByRole("tab", { name: "Deal information" }));
    expect(view.getByText("opening_price")).toBeTruthy();
    expect(view.queryByText("order-1")).toBeNull();

    fireEvent.click(view.getByRole("button", { name: "Hide" }));
    expect(view.queryByRole("tab", { name: "Deal information" })).toBeNull();
    expect(view.queryByText("opening_price")).toBeNull();

    fireEvent.click(view.getByRole("button", { name: "Show" }));
    expect(
      view
        .getByRole("tab", { name: "Deal information" })
        .getAttribute("aria-selected"),
    ).toBe("true");
    expect(view.getByText("opening_price")).toBeTruthy();
  });

  it("starts collapsed when the bot has no orders", () => {
    const view = render(<BotInfo bot={{ ...singleBot, orders: [] }} />);

    expect(view.queryByRole("tab", { name: "Orders information" })).toBeNull();
    fireEvent.click(view.getByRole("button", { name: "Show" }));
    expect(view.getByRole("tab", { name: "Orders information" })).toBeTruthy();
    expect(view.getByRole("tab", { name: "Deal information" })).toBeTruthy();
  });
});
