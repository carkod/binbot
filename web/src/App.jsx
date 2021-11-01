import React from "react";
import Login from "./containers/login/Login";
import { Redirect, Route } from "react-router-dom";
import { getToken } from "./request";
import { checkValue } from "./validations";
import Admin from "./layouts/Admin.jsx";
import NotFound from "./pages/NotFound";

export default function App() {
  const token = getToken();
  return (
    <>
    {!checkValue(token) ?
      <>
        <Route exact path="/" render={() => <Redirect to="/admin/dashboard" /> } />
        <Route exact path="/admin" render={() => <Redirect to="/admin/dashboard" /> } />
        <Route exact path="/login" render={() => <Redirect to="/admin/dashboard" /> } />
        <Route render={(props) => <Admin path="/admin/dashboard" {...props} /> }/>
        <Route component={NotFound} /> 
      </>
    : <Route component={Login} /> 
    }
    </>
  );
}
