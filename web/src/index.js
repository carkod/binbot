import "bootstrap/dist/css/bootstrap.css";
import { createBrowserHistory } from "history";
import React from "react";
import ReactDOM from "react-dom";
import { Provider } from "react-redux";
import { BrowserRouter, Switch } from "react-router-dom";
import App from "./App.jsx";
import "./assets/scss/paper-dashboard.scss";
import reportWebVitals from "./reportWebVitals";
import configureStore from "./store";

const store = configureStore({});

ReactDOM.render(
  <Provider store={store}>
    <BrowserRouter>
      <Switch>
        <App />
      </Switch>
    </BrowserRouter>
  </Provider>,
  document.getElementById("root")
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
