import {
  checkValue,
  floorToMultiple,
  isPositiveFinite,
  percentageToFloat,
  roundDecimals,
  toPercentage,
} from "./math";

describe("checkValue", () => {
  it.each(["", null, undefined])("identifies missing input (%s)", (value) => {
    expect(checkValue(value)).toBe(true);
  });

  it.each([0, -1, "0", "-1", "1", false, NaN])(
    "does not treat supplied input as missing (%s)",
    (value) => {
      expect(checkValue(value)).toBe(false);
    },
  );

  it("allows zero, signed values and numeric strings in percentage conversions", () => {
    expect(toPercentage(0)).toBe(0);
    expect(toPercentage("-0.05")).toBe(-5);
    expect(percentageToFloat("0")).toBe(0);
    expect(percentageToFloat(-5)).toBe(-0.05);
    expect(toPercentage(null)).toBeNull();
    expect(percentageToFloat("")).toBeNull();
  });
});

describe("floorToMultiple", () => {
  it.each([
    [0, 60_000, 0],
    [59_999, 60_000, 0],
    [60_000, 60_000, 60_000],
    [60_001, 60_000, 60_000],
    [1_799_999, 900_000, 900_000],
    [1_800_000, 900_000, 1_800_000],
    [-1, 60_000, -60_000],
  ])("rounds %s down to a multiple of %s", (value, interval, expected) => {
    expect(floorToMultiple(value, interval)).toBe(expected);
  });
});

describe("isPositiveFinite", () => {
  it.each([Number.MIN_VALUE, 0.0001, 1, Number.MAX_VALUE])(
    "accepts positive finite numbers (%s)",
    (value) => {
      expect(isPositiveFinite(value)).toBe(true);
    },
  );

  it.each([0, -0, -1, NaN, Infinity, -Infinity])(
    "rejects zero, negative and non-finite numbers (%s)",
    (value) => {
      expect(isPositiveFinite(value)).toBe(false);
    },
  );
});

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

  it("should remove trailing zeroes", () => {
    expect(roundDecimals(56.0000000000001, 2)).toBe(56);
    expect(roundDecimals(56.1000000000001, 2)).toBe(56.1);
    expect(roundDecimals(56.1200000000001, 2)).toBe(56.12);
  });
});

describe("toPercentage", () => {
  it("rounds after scaling and removes floating point tails", () => {
    expect(toPercentage(0.56)).toBe(56);
    expect(toPercentage(0.5600000000000001)).toBe(56);
    expect(toPercentage(0.561, 1)).toBe(56.1);
  });
});
