import React, { Component } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Form, FormFeedback, FormGroup,
  Input,
  Row
} from "reactstrap";
import { checkValue } from "../validations";

class LoginForm extends Component {
  state = {
    username: "",
    usernameIsRequiredError: false,
    password: "",
    email: "",
    emailIsRequiredError: false,
    description: "",
    passwordNotMatch: false,
    passwordIsRequiredError: false,
  };

  requiredinValidation = () => {
    const { email, password } = this.state;
    if (!checkValue(email)) {
      this.setState({ emailIsRequiredError: true, formIsValid: false });
    } else {
      this.setState({ emailIsRequiredError: false });
    }

    if (!checkValue(password)) {
      this.setState({ passwordIsRequiredError: true, formIsValid: false });
    } else {
      this.setState({ passwordIsRequiredError: false });
    }

    this.setState({ formIsValid: true });
  };

  handleChange = (e) => {
    this.requiredinValidation();
    this.setState({ [e.target.name]: e.target.value });
  };

  handleSubmit = (e) => {
    e.preventDefault();
    this.requiredinValidation();
    if (this.state.formIsValid) {
      const { email, password } = this.state;
      this.props.onSubmit({
        email: email,
        password: password
      });
    }
  };

  render() {
    const { passwordIsRequiredError, emailIsRequiredError } = this.state;
    return (
      <div className="c-login-card">
      <Card className="card-user">
        <CardHeader>
        <CardTitle tag="h3">Login</CardTitle>
        </CardHeader>
        <CardBody>
          <Form onSubmit={this.handleSubmit}>
            <Row>
              <Col md="12">
                <FormGroup>
                  <label htmlFor="email">Email address</label>
                  <Input
                    invalid={emailIsRequiredError}
                    placeholder="Email"
                    type="email"
                    name="email"
                    autocomplete="on"
                    onChange={this.handleChange}
                  />
                  <FormFeedback>Email is required</FormFeedback>
                </FormGroup>
              </Col>
              <Col md="12">
                <FormGroup>
                  <label htmlFor="password">Password</label>
                  <Input
                    invalid={passwordIsRequiredError}
                    type="password"
                    name="password"
                    autocomplete="on"
                    onChange={this.handleChange}
                  />
                  <FormFeedback className="register-form__error">
                    Password is required
                  </FormFeedback>
                </FormGroup>
              </Col>
            </Row>
            <Row>
              <div className="update ml-auto mr-auto">
                <Button className="btn-round" color="primary" type="submit">
                  Login
                </Button>
              </div>
            </Row>
          </Form>
        </CardBody>
      </Card>
      </div>
    );
  }
}

export default LoginForm;
