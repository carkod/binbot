import { configureStore } from "@reduxjs/toolkit";
import { rootReducer } from "../store";

const mockStore = () => {
  return configureStore({
    reducer: rootReducer,
  });
};

export default mockStore;
