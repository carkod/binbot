import React from "react";
import Login from "./containers/login/Login";
import Admin from "./layouts/Admin.jsx";
import { Redirect, Route } from "react-router-dom";
import { getToken } from "./request";

export default function App() {
  return (
    <>
      <Route exact path="/login" component={Login} />
      <Route exact path="/" render={() => <Redirect to="/admin/dashboard" />} />
      <Route
        render={(props) =>
          !!getToken() ? (
            <Admin path="/admin/dashboard" {...props} />
          ) : (
            <Redirect to="/login" {...props} />
          )
        }
      />
    </>
  );
}
