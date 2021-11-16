import React, { Component } from "react";
import { connect } from "react-redux";
import ReduxToastr from "react-redux-toastr";
import { Redirect } from "react-router";
import LoginForm from "../../components/LoginForm";
import { login } from "./actions";

class Login extends Component {

  constructor() {
    super();
    this.state = {
      redirect: false,
    }
  }

  componentDidUpdate = (p, s) => {
    if (this.props.accessToken !== p.accessToken) {
      this.setState({ redirect: true })
    }
  }

  handleSubmit = (data) => {
    const credentials = {
      email: data.email,
      password: data.password,
      username: data.username,
      description: data.description,
    };
    this.props.login(credentials);
  };

  render() {
    // Redirect to dashboard when hitting /login and already authenticated
    if (this.state.redirect) {
      return <Redirect to="/admin/dashboard" />
    } else {
      return (
        <div className="content">
          <ReduxToastr
            timeOut={4000}
            newestOnTop={true}
            preventDuplicates
            position="top-right"
            getState={(state) => state.toastr} // This is the default
            transitionIn="fadeIn"
            transitionOut="fadeOut"
            progressBar
            closeOnToastrClick
          />
          <LoginForm onSubmit={this.handleSubmit} />
        </div>
      );
    }
  }
}

const mapStateToProps = (state) => {
  const { email, access_token, password } = state.loginReducer;

  return {
    email: email,
    password: password,
    accessToken: access_token
  };
};

export default connect(mapStateToProps, { login })(
  Login
);
