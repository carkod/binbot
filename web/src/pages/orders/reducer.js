import { GET_ALL_ORDERS, GET_ALL_ORDERS_ERROR, GET_ALL_ORDERS_SUCCESS, GET_OPEN_ORDERS, GET_OPEN_ORDERS_ERROR, GET_OPEN_ORDERS_SUCCESS, POLL_ORDERS, POLL_ORDERS_ERROR, POLL_ORDERS_SUCCESS } from "./actions";


// The initial state of the App
export const initialState = {
  isLoading: false,
  isError: false,
  data: null,
  message: null,
  params: null,
  pages: null,
};

function ordersReducer(state = initialState, action) {
  switch (action.type) {
    case GET_ALL_ORDERS: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        params: action.data,
        data: null,
      };

      return newState;
    }
    case GET_ALL_ORDERS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: action.orders,
        pages: action.pages
      };
      return newState;
    }

    case GET_ALL_ORDERS_ERROR: {
      return {
        ...state,
        error: action.error,
        isLoading: false,
        isError: true,
      };
    }

    case GET_OPEN_ORDERS: {
      const newState = {
        ...state,
        isLoading: true,
        isError: false,
        data: state.data
      };

      return newState;
    }
    case GET_OPEN_ORDERS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: state.data.concat(x => x._id.$oid === action.data)
      };
      return newState;
    }

    case GET_OPEN_ORDERS_ERROR: {
      return {
        ...state,
        error: action.error,
        isLoading: false,
        isError: true,
        data: action.data
      };
    }

    case POLL_ORDERS: {
      const newState = {
        isLoading: true,
        isError: false,
        data: state.data
      };

      return newState;
    }
    case POLL_ORDERS_SUCCESS: {
      const newState = {
        ...state,
        isLoading: false,
        isError: false,
        data: state.data.filter(x => x._id.$oid !== action.data)
      };
      return newState;
    }

    case POLL_ORDERS_ERROR: {
      return {
        ...state,
        error: action.error,
        isLoading: false,
        isError: true,
      };
    }

    default:
      return state;
  }
}

export { ordersReducer };
