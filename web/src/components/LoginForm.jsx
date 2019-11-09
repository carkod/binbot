import React, { Component } from "react";
// reactstrap components
import { Button, Card, CardBody, CardHeader, CardTitle, Col, Form, FormGroup, Input, Row, FormFeedback } from "reactstrap";


class LoginForm extends Component {


  state = {
    username: '',
    usernameIsRequiredError: false,
    password: '',
    confirmPassword: '',
    email: '',
    emailIsRequiredError: false,
    description: '',
    passwordNotMatch: false,
    passwordIsRequiredError: false,
  }

  requiredinValidation = () => {
    const { username, password } = this.state;
    if (username === '' || username === null || username === undefined) {
      this.setState({ usernameIsRequiredError: true });
    } else {
      this.setState({ usernameIsRequiredError: false });
    }

    if (password === '' || password === null || password === undefined) {
      this.setState({ passwordIsRequiredError: true });
    } else {
      this.setState({ passwordIsRequiredError: false });
    }

  }

  passwordMatchinValidation = () => {
    if (this.state.confirmPassword !== this.state.password) {
      this.setState({ passwordNotMatch: true });
    } else {
      this.setState({ passwordNotMatch: false });
    }
  }

  handleChange = (e) => {
    this.requiredinValidation();
    this.passwordMatchinValidation();
    this.setState({ [e.target.name]: e.target.value });
  }

  handleSubmit = (e) => {
    e.preventDefault();
    // this.requiredinValidation();
    this.passwordMatchinValidation();
    this.props.onSubmit(this.state);
  }

  render() {
    return (
      <Card className="card-user">
        <CardHeader>
          <CardTitle tag="h5">Login</CardTitle>
        </CardHeader>
        <CardBody>
          <Form onSubmit={this.handleSubmit}>
            <Row>
              <Col className="pr-1" md="12">
                <FormGroup>
                  <label htmlFor="email">Email address</label>
                  <Input placeholder="Email" type="email" name="email" onChange={this.handleChange} />
                  {this.state.emailIsRequiredError && <FormFeedback className="register-form__error">Email is required</FormFeedback>}
                </FormGroup>
              </Col>
            </Row>
            <Row>
              <Col className="pr-1" md="12">
                <FormGroup>
                  <label>Password</label>
                  <Input type="password" name="password" onChange={this.handleChange} />
                  {/* <FormFeedback invalid className="register-form__error">Password is required</FormFeedback> */}
                </FormGroup>
              </Col>
            </Row>
            <Row>
              <div className="update ml-auto mr-auto">
                <Button
                  className="btn-round"
                  color="primary"
                  type="submit"
                >Login</Button>
              </div>
            </Row>
          </Form>
        </CardBody>
      </Card>
    )
  }
}


export default LoginForm;
