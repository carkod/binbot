import { singleBot } from "../../features/bots/botInitialState";
import { BotPosition, BotStatus, EntryMode } from "../enums";
import { percentageFromOrderLine } from "./editing";
import { dealColors, updateOrderLines, updateTimescaleMarks } from "./index";
import { matchTsToTimescale } from "../time";

it.each([
  ["stop_loss", BotPosition.LONG, 97, 100, 3],
  ["stop_loss", BotPosition.SHORT, 103, 100, 3],
  ["trailing_profit", BotPosition.LONG, 106, 100, 6],
  ["trailing_profit", BotPosition.SHORT, 94, 100, 6],
  ["trailing_deviation", BotPosition.LONG, 101.76, 106, 4],
  ["trailing_deviation", BotPosition.SHORT, 97.76, 94, 4],
] as const)(
  "converts %s for %s using the correct reference",
  (field, position, price, reference, expected) => {
    expect(percentageFromOrderLine(field, price, reference, position)).toBe(
      expected,
    );
  },
);
it("rejects wrong-side and nonfinite drops", () => {
  expect(
    percentageFromOrderLine("stop_loss", 101, 100, BotPosition.LONG),
  ).toBeNull();
  expect(
    percentageFromOrderLine("trailing_profit", 101, 100, BotPosition.SHORT),
  ).toBeNull();
  expect(
    percentageFromOrderLine("trailing_deviation", NaN, 100, BotPosition.LONG),
  ).toBeNull();
});
it.each([BotPosition.LONG, BotPosition.SHORT])(
  "projects conditional %s risk from entry and adds entry/expiry marks",
  (position) => {
    const bot = {
      ...singleBot,
      pair: "XBTUSDTM",
      position,
      fiat_order_size: 100,
      entry_mode: EntryMode.CONDITIONAL_LIMIT,
      entry_price: 100,
      created_at: 1800000000000,
      entry_expires_at: 1800021600000,
      trailing: true,
      trailing_profit: 6,
      trailing_deviation: 4,
    };
    const lines = updateOrderLines(bot, 120);
    expect(lines.find((line) => line.id === "entry_price")).toMatchObject({
      price: 100,
      color: dealColors.entry_price,
    });
    expect(lines.find((line) => line.id === "stop_loss")?.price).toBe(
      position === BotPosition.LONG ? 97 : 103,
    );
    expect(
      Object.entries(dealColors)
        .filter(([id]) => id !== "entry_price")
        .every(([, color]) => color !== dealColors.entry_price),
    ).toBe(true);
    expect(updateTimescaleMarks(bot)).toEqual([
      expect.objectContaining({
        id: "conditional_entry",
        label: "E",
        time: matchTsToTimescale(bot.created_at),
      }),
      expect.objectContaining({
        id: "conditional_entry_expiry",
        label: "X",
        time: matchTsToTimescale(bot.entry_expires_at),
      }),
    ]);
    expect(
      updateTimescaleMarks({ ...bot, entry_mode: EntryMode.IMMEDIATE }),
    ).toEqual([]);
    expect(
      updateOrderLines({ ...bot, status: BotStatus.ACTIVE }, 120).some(
        (line) => line.id === "entry_price",
      ),
    ).toBe(false);
  },
);
