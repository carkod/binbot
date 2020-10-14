import React from "react";
import ReactDOM from "react-dom";
import { createBrowserHistory } from "history";
import { Router, Route, Switch, Redirect } from "react-router-dom";
import { Provider } from "react-redux"
import configureStore from './store'

import "bootstrap/dist/css/bootstrap.css";
import "assets/scss/paper-dashboard.scss?v=1.1.0";
import "perfect-scrollbar/css/perfect-scrollbar.css";

import AdminLayout from "layouts/Admin.jsx";
import Login from 'containers/login/Login'
import { getToken } from "./request";

const hist = createBrowserHistory();
const store = configureStore({});

ReactDOM.render(
  <Provider store={store}>
    <Router history={hist}>
      <Switch>
        <Route exact path="/login" component={Login} />
        <Route exact path="/" render={() => <Redirect to="/admin/dashboard" />} />
        <Route render={props => 
          !!getToken() ?
          <AdminLayout path="/admin/dashboard" {...props} /> :
          <Redirect to="/login" {...props} />
        } />
        </Switch>
    </Router>
  </Provider>
  ,
  document.getElementById("root")
);
