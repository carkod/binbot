import LoginForm from "components/LoginForm";
import { setToken } from "containers/request";
import React, { Component } from "react";
import { connect } from "react-redux";
// reactstrap components
import { Col, Row } from "reactstrap";
import { login, loginSucceeded, loginFailed } from './actions';

class Login extends Component {

  handleSubmit = async (data) => {
    this.props.login(data);
    const url = 'http://localhost:5000/user/login';
    const credentials = {
      email: data.email,
      password: data.password,
      username: data.username,
      description: data.description
    }
    const params = {
      method: 'POST', // *GET, POST, PUT, DELETE, etc.
      mode: 'cors', // no-cors, *cors, same-origin
      // cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
      // credentials: 'same-origin', // include, *same-origin, omit
      headers: new Headers({ 'Content-Type': 'application/json'}),
      body: JSON.stringify(credentials) // body data type must match "Content-Type" header
    }
    let response = await fetch(url, params);
    if (!response.ok) {
      this.props.loginFailed(response)
    } 
    const user = await response.json();
    setToken(user.access_token)
    this.props.loginSucceeded(user);
    this.props.history.push('/');
  }

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
  return {}
}

export default connect(mapStateToProps, { login, loginSucceeded })(Login);
