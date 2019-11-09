import LoginForm from "components/LoginForm";
import React, { Component } from "react";
import { connect } from "react-redux";
// reactstrap components
import { Col, Row } from "reactstrap";
import { login } from './actions';

class Login extends Component {

  handleSubmit = (data) => {
    this.props.login(data);
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
  console.log(state);
  return {}
}

export default connect(mapStateToProps, { login })(Login);
