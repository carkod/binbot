import type { Action, ThunkAction } from "@reduxjs/toolkit";
import { combineSlices, configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { layoutSlice } from "../features/layoutSlice";
import { userApiSlice } from "../features/userApiSlice";
import { botSlice } from "../features/bots/botSlice";
import { binanceApiSlice } from "../features/binanceApiSlice";
import { autotradeSettingsSlice } from "../features/autotradeSlice";

export const rootReducer = combineSlices(
  userApiSlice,
  layoutSlice,
  botSlice,
  binanceApiSlice,
  autotradeSettingsSlice
);

export type RootState = ReturnType<typeof rootReducer>;

// The store setup is wrapped in `makeStore` to allow reuse
// when setting up tests that need the same store config
export const makeStore = (preloadedState?: Partial<RootState>) => {
  const store = configureStore({
    reducer: rootReducer,
    // Adding the api middleware enables caching, invalidation, polling,
    // and other useful features of `rtk-query`.
    middleware: (getDefaultMiddleware) => {
      return getDefaultMiddleware()
        .concat(userApiSlice.middleware)
        .concat(binanceApiSlice.middleware);
    },
    preloadedState,
    devTools: process.env.NODE_ENV !== "production",
  });
  // configure listeners using the provided defaults
  // optional, but required for `refetchOnFocus`/`refetchOnReconnect` behaviors
  setupListeners(store.dispatch);
  return store;
};

export const store = makeStore();

// Infer the type of `store`
export type AppStore = typeof store;
// Infer the `AppDispatch` type from the store itself
export type AppDispatch = AppStore["dispatch"];
export type AppThunk<ThunkReturnType = void> = ThunkAction<
  ThunkReturnType,
  RootState,
  unknown,
  Action
>;
