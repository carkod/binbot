import React, { Component } from "react";
// reactstrap components
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Form,
  FormGroup,
  Input,
  Row,
  FormFeedback,
} from "reactstrap";

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
    if (email === "" || email === null || email === undefined) {
      this.setState({ emailIsRequiredError: true, formIsValid: false });
    } else {
      this.setState({ emailIsRequiredError: false });
    }

    if (password === "" || password === null || password === undefined) {
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
      this.props.onSubmit(this.state);
    }
  };

  render() {
    const { passwordIsRequiredError, emailIsRequiredError } = this.state;
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
                  <Input
                    invalid={emailIsRequiredError}
                    placeholder="Email"
                    type="email"
                    name="email"
                    onChange={this.handleChange}
                  />
                  <FormFeedback>Email is required</FormFeedback>
                </FormGroup>
              </Col>
            </Row>
            <Row>
              <Col className="pr-1" md="12">
                <FormGroup>
                  <label htmlFor="password">Password</label>
                  <Input
                    invalid={passwordIsRequiredError}
                    type="password"
                    name="password"
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
    );
  }
}

export default LoginForm;
