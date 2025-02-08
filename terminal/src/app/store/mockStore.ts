import { configureStore } from '@reduxjs/toolkit';
import rootReducer from './rootReducer'; // Import your root reducer

const initialState = {
  // Define your initial state here
  bots: {
    entities: {},
    ids: [],
    totalProfit: 0,
  },
  // ...other slices
};

const mockStore = (state = initialState) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState: state,
  });
};

export default mockStore;
