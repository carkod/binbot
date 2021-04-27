import React, { Component } from "react";
import { connect } from "react-redux";
import LoginForm from "../../components/LoginForm";
import { login, loginFailed, loginSucceeded } from "./actions";
import ReduxToastr from "react-redux-toastr";
import { getToken } from "../../request";
import { checkValue } from "../../validations";

class Login extends Component {

  componentDidUpdate = () => {
    if (!checkValue(getToken())) {
      this.props.history.push("/");
    }
  }

  handleSubmit = async (data) => {
    const credentials = {
      email: data.email,
      password: data.password,
      username: data.username,
      description: data.description,
    };
    this.props.login(credentials);
  };

  render() {
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

const mapStateToProps = (p, s) => {
  const { loginReducer } = p;
  return {
    message: loginReducer.message,
    data: loginReducer.data
  };
};

export default connect(mapStateToProps, { login, loginSucceeded, loginFailed })(
  Login
);
