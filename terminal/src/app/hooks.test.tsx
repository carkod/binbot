import { act, render, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { vi } from "vitest";

import type { ISymbol } from "../features/symbolsApiSlice";
import { useSymbolDataProvider } from "./hooks";

const mockTriggerGetOneSymbol = vi.hoisted(() => vi.fn());

vi.mock("../features/symbolsApiSlice", async () => {
  const actual = await vi.importActual("../features/symbolsApiSlice");

  return {
    ...actual,
    useGetSymbolsQuery: vi.fn(() => ({ data: [] })),
    useLazyGetOneSymbolQuery: vi.fn(() => [mockTriggerGetOneSymbol]),
  };
});

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error?: unknown) => void;
};

const createDeferred = <T,>(): Deferred<T> => {
  let resolve: (value: T) => void = () => undefined;
  let reject: (error?: unknown) => void = () => undefined;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });

  return { promise, resolve, reject };
};

describe("useSymbolDataProvider", () => {
  beforeEach(() => {
    mockTriggerGetOneSymbol.mockReset();
  });

  it("ignores stale symbol metadata responses when a newer pair is selected", async () => {
    const routeSymbolRequest = createDeferred<Partial<ISymbol>>();
    const selectedSymbolRequest = createDeferred<Partial<ISymbol>>();
    const latestState: {
      quoteAsset?: string;
      baseAsset?: string;
      futuresLeverage?: number;
    } = {};

    mockTriggerGetOneSymbol.mockImplementation((pair: string) => ({
      unwrap: () =>
        pair === "KOMAUSDTM"
          ? routeSymbolRequest.promise
          : selectedSymbolRequest.promise,
    }));

    const TestComponent = () => {
      const symbolData = useSymbolDataProvider();

      latestState.quoteAsset = symbolData.quoteAsset;
      latestState.baseAsset = symbolData.baseAsset;
      latestState.futuresLeverage = symbolData.futuresLeverage;

      useEffect(() => {
        symbolData.updateQuoteBaseState("KOMAUSDTM");
        symbolData.updateQuoteBaseState("BTCUSDTM");
      }, [symbolData.updateQuoteBaseState]);

      return null;
    };

    render(<TestComponent />);

    await act(async () => {
      selectedSymbolRequest.resolve({
        quote_asset: "USDT",
        base_asset: "BTC",
        futures_leverage: 3,
      });
    });

    await waitFor(() => {
      expect(latestState.baseAsset).toBe("BTC");
      expect(latestState.futuresLeverage).toBe(3);
    });

    await act(async () => {
      routeSymbolRequest.resolve({
        quote_asset: "USDT",
        base_asset: "KOMA",
        futures_leverage: 5,
      });
    });

    expect(latestState.quoteAsset).toBe("USDT");
    expect(latestState.baseAsset).toBe("BTC");
    expect(latestState.futuresLeverage).toBe(3);
  });
});
