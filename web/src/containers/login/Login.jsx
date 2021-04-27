import LoginForm from "../../components/LoginForm";
import React, { Component } from "react";
import { connect } from "react-redux";
import { Col, Row } from "reactstrap";
import { login, loginSucceeded, loginFailed } from "./actions";

class Login extends Component {
  handleSubmit = async (data) => {
    const credentials = {
      email: data.email,
      password: data.password,
      username: data.username,
      description: data.description,
    };
    this.props.login(credentials);
    this.props.history.push("/");
  };

  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              <LoginForm onSubmit={this.handleSubmit} />
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  return {};
};

export default connect(mapStateToProps, { login, loginSucceeded, loginFailed })(
  Login
);
