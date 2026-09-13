import { render } from "@testing-library/react";

import { singleBot } from "../../../features/bots/botInitialState";
import BotInfo from "../BotInfo";

describe("BotInfo", () => {
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

    expect(view.getByText("current_position_qty")).toBeTruthy();
    expect(view.getByText("922")).toBeTruthy();
  });
});
