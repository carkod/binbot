import { matchTsToTimescale, renderDuration } from "./time";

it("preserves order and expiry times within a candle at any chart interval", () => {
  const timestamp = Date.parse("2026-11-20T12:37:42.567Z");

  expect(matchTsToTimescale(timestamp)).toBe(1795178262);
  expect(matchTsToTimescale(String(timestamp))).toBe(1795178262);
});

it("uses the deal timestamps for completed bot durations", () => {
  expect(
    renderDuration({
      deal: {
        opening_timestamp: Date.parse("2026-11-19T10:15:00Z"),
        closing_timestamp: Date.parse("2026-11-20T12:37:42Z"),
      },
    }),
  ).toBe("1d 2h 22m 42s");
});
