import { createContext } from "react";

export const SpinnerContext = createContext({
  spinner: false,
  setSpinner: (_value: boolean) => {},
});
