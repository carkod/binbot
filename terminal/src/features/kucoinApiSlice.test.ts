import {
  describe as describeBlock,
  expect as expectValue,
  it as testCase,
} from "vitest";
import { vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { kucoinApiSlice, transformBtcCloseSeries } from "./kucoinApiSlice";

describeBlock("transformBtcCloseSeries", () => {
  testCase(
    "timestamps KuCoin closes at the end of each 15-minute candle",
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
          new Date(1710000900000).toISOString(),
          new Date(1710001800000).toISOString(),
        ],
        close: [101.5, 102.5],
      });
    },
  );
});

class MockRequest {
  url: string;

  constructor(input: RequestInfo | URL) {
    this.url = String(input);
  }

  clone() {
    return this;
  }
}

describeBlock("futuresLiquidity query", () => {
  const bookResponse = {
    code: "200000",
    data: {
      symbol: "KGENUSDTM",
      ts: 1_790_000_000_000_000_000,
      bids: [[99.96, 200]],
      asks: [[100.04, 200]],
    },
  };
  const contractResponse = {
    code: "200000",
    data: {
      symbol: "KGENUSDTM",
      multiplier: 0.001,
      quoteCurrency: "USDT",
      isInverse: false,
    },
  };

  afterEach(() => vi.unstubAllGlobals());

  const runQuery = async (
    book: unknown = bookResponse,
    contract: unknown = contractResponse,
    bookStatus = 200,
  ) => {
    vi.stubGlobal("Request", MockRequest);
    const fetchMock = vi.fn(async (request: MockRequest) => {
      const isBook = request.url.includes("/level2/depth100");
      return new Response(JSON.stringify(isBook ? book : contract), {
        status: isBook ? bookStatus : 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const store = configureStore({
      reducer: { [kucoinApiSlice.reducerPath]: kucoinApiSlice.reducer },
      middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(kucoinApiSlice.middleware),
    });
    const result = await store.dispatch(
      kucoinApiSlice.endpoints.futuresLiquidity.initiate("KGENUSDTM"),
    );
    store.dispatch(kucoinApiSlice.util.resetApiState());
    return { result, fetchMock };
  };

  testCase(
    "uses the existing proxy and exchange multiplier to value the book",
    async () => {
      const { result, fetchMock } = await runQuery();
      expectValue(result.data).toMatchObject({
        liquidity: "Low liquidity",
        obi: expectValue.any(Number),
        timestamp: 1_790_000_000_000,
      });
      expectValue(result.data?.spreadRatio).toBeCloseTo(0.0008);
      expectValue(result.data?.bidDepth).toBeCloseTo(19.992);
      expectValue(result.data?.askDepth).toBeCloseTo(20.008);
      expectValue(fetchMock.mock.calls.map(([request]) => request.url)).toEqual(
        [
          "/kucoin-futures/api/v1/level2/depth100?symbol=KGENUSDTM",
          "/kucoin-futures/api/v1/contracts/KGENUSDTM",
        ],
      );
    },
  );

  testCase(
    "rejects KuCoin application errors returned with HTTP success",
    async () => {
      const { result } = await runQuery({
        code: "400100",
        msg: "Symbol not found",
      });
      expectValue(result.error).toMatchObject({ status: "CUSTOM_ERROR" });
      expectValue(result.data).toBeUndefined();
    },
  );

  testCase(
    "preserves HTTP failures instead of labeling liquidity",
    async () => {
      const { result } = await runQuery(
        { message: "Rate limited" },
        contractResponse,
        429,
      );
      expectValue(result.error).toMatchObject({ status: 429 });
      expectValue(result.data).toBeUndefined();
    },
  );

  testCase.each([
    { ...contractResponse, data: { ...contractResponse.data, multiplier: 0 } },
    {
      ...contractResponse,
      data: { ...contractResponse.data, isInverse: true },
    },
    {
      ...contractResponse,
      data: { ...contractResponse.data, symbol: "XBTUSDTM" },
    },
    {
      ...contractResponse,
      data: { ...contractResponse.data, quoteCurrency: "BTC" },
    },
  ])("rejects invalid or mismatched contract metadata", async (contract) => {
    const { result } = await runQuery(bookResponse, contract);
    expectValue(result.error).toMatchObject({ status: "CUSTOM_ERROR" });
    expectValue(result.data).toBeUndefined();
  });
});
