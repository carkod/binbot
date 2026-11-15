import type { TradeFlowHistory } from "../features/kucoinTradeFlow";

const DATABASE_NAME = "binbot-microstructure";
const STORE_NAME = "tradeFlow";

interface StoredTradeFlow {
  symbol: string;
  multiplier: number;
  history: TradeFlowHistory;
}

const openDatabase = (): Promise<IDBDatabase> =>
  new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME, { keyPath: "symbol" });
    };
    request.onerror = () => reject(request.error);
    request.onblocked = () =>
      reject(new Error("Browser history storage blocked"));
    request.onsuccess = () => resolve(request.result);
  });

export const loadTradeFlowHistory = async (
  symbol: string,
  multiplier: number,
): Promise<TradeFlowHistory> => {
  const database = await openDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, "readonly");
      const request = transaction.objectStore(STORE_NAME).get(symbol);
      transaction.oncomplete = () => {
        const stored = request.result as StoredTradeFlow | undefined;
        resolve(
          stored?.multiplier === multiplier
            ? stored.history
            : { buckets: [], seen: {} },
        );
      };
      transaction.onabort = () => reject(transaction.error);
      transaction.onerror = () => reject(transaction.error);
    });
  } finally {
    database.close();
  }
};

export const saveTradeFlowHistory = async (
  symbol: string,
  multiplier: number,
  history: TradeFlowHistory,
): Promise<void> => {
  const database = await openDatabase();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = database.transaction(STORE_NAME, "readwrite");
      transaction
        .objectStore(STORE_NAME)
        .put({ symbol, multiplier, history } satisfies StoredTradeFlow);
      transaction.oncomplete = () => resolve();
      transaction.onabort = () => reject(transaction.error);
      transaction.onerror = () => reject(transaction.error);
    });
  } finally {
    database.close();
  }
};
