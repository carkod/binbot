import {
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
} from "vitest";
import { transformBtcCloseSeries } from "./kucoinApiSlice";

describeBlock("transformBtcCloseSeries", () => {
  testCase(
    "sorts KuCoin futures candles and selects only timestamps and closes",
    () => {
      const result = transformBtcCloseSeries({
        code: "200000",
        data: [
          [1710000900000, 101, 103, 100, 102.5, 10, 1025],
          [1710000000000, "100", "102", "99", "101.5", "12", "1218"],
        ],
      });

      expectValue(result).toEqual({
        symbol: "XBTUSDTM",
        interval: "15m",
        timestamp: [
          new Date(1710000000000).toISOString(),
          new Date(1710000900000).toISOString(),
        ],
        close: [101.5, 102.5],
      });
    },
  );
});
