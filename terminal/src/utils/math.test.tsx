import { roundDecimals } from "./math";

describe("roundDecimals", () => {
  it("should round to 2 decimals by default", () => {
    expect(roundDecimals(7.000000000000001)).toBe(7);
    expect(roundDecimals(7.005)).toBe(7.01);
    expect(roundDecimals(7.004)).toBe(7);
    expect(roundDecimals(-7.005)).toBe(-7.01);
    expect(roundDecimals(-7.004)).toBe(-7);
  });

  it("should round to specified decimals", () => {
    expect(roundDecimals(7.123456, 4)).toBe(7.1235);
    expect(roundDecimals(7.123444, 4)).toBe(7.1234);
    expect(roundDecimals(0.1 + 0.2, 2)).toBe(0.3);
    expect(roundDecimals(0.00021150000000000002, 7)).toBe(0.0002115);
  });

  it("should handle zero and negative numbers", () => {
    expect(roundDecimals(0)).toBe(0);
    expect(roundDecimals(-0.12345, 3)).toBe(-0.123);
  });
});
