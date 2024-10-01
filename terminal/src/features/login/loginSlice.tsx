import { type PayloadAction } from '@reduxjs/toolkit';
import { createAppSlice } from '../../app/createAppSlice';

// Define the initial state using an interface
interface LoginState {
  access_token: string | null;
  email: string | null;
  password: string | null;
  username: string | null;
  error: boolean;
  message: string | null;
}

const initialState: LoginState = {
  access_token: null,
  email: null,
  password: null,
  username: null,
  error: false,
  message: null,
};

// Define the payload types for the actions
interface LoginPayload {
  email: string;
  password: string;
}

interface LoginSuccessPayload {
  access_token: string;
  email: string;
}

interface LoginErrorPayload {
  isError: boolean;
  message: string;
}

// Create a slice
export const loginSlice = createAppSlice({
  name: 'login',
  initialState,
  reducers: {
    login(state, action: PayloadAction<LoginPayload>) {
      state.password = action.payload.password;
      state.username = action.payload.email;
    },
    loginSuccess(state, action: PayloadAction<LoginSuccessPayload>) {
      state.access_token = action.payload.access_token;
      state.email = action.payload.email;
    },
    loginError(state, action: PayloadAction<LoginErrorPayload>) {
      state.error = action.payload.isError;
      state.message = action.payload.message;
    },
  },
  selectors: {
    selectAccessToken: state => state.access_token,
    selectEmail: state => state.email,
    selectPassword: state => state.password,
    selectUsername: state => state.username,
    selectError: state => state.error,
    selectMessage: state => state.message,
  },
});

// Export the actions
export const { login, loginSuccess, loginError } = loginSlice.actions;

// Export the reducer
export const { selectAccessToken, selectEmail, selectPassword, selectUsername, selectError, selectMessage } = loginSlice.selectors;
