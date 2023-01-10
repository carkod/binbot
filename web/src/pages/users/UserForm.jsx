import React, { useEffect, useRef, useState } from "react";
import { Button, Col, Form, FormFeedback, FormGroup, Input, Label, Row } from "reactstrap";
import { checkValue } from "../../validations";

const UserForm = ({ currentUser, handleSubmit }) => {
  let mounted = useRef();
  const [id, setId] = useState(null)
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [about, setAbout] = useState("");

  useEffect(() => {
    if (!mounted.current) {
      // do componentDidMount logic
      
      mounted.current = true;
    } else {
      if (!checkValue(currentUser) && currentUser.id !== id) {
        setEmail(currentUser.email);
        setUsername(currentUser.username);
        setPassword(currentUser.password);
        setAbout(currentUser.about);
        setId(currentUser.id)
      }
    }
  }, [currentUser, id]);

  const validateFields = () => {
    if (checkValue(email)) {
      setEmailError("Email is required!")
    }
    if (checkValue(password)) {
      setPasswordError("Password is required!")
    }
    return false
  }

  const onSubmit = (e) => {
    e.preventDefault();
    validateFields();
    const submitForm = {
      id: currentUser?.id,
      email: email,
      password: password,
      username: username || "",
      description: about || "",
    }
    handleSubmit(submitForm)
  }

  return (
    <Form onSubmit={onSubmit}>
      <Row>
        <Col className="pr-1" md="5">
          <FormGroup>
            <Label htmlFor="email">Email (login)</Label>
            <Input
              name="email"
              defaultValue={email}
              placeholder="email"
              type="email"
              onChange={(e) => setEmail(e.target.value)}
            />
            {!checkValue(emailError) && (
              <FormFeedback className="register-form__error">
                Email is required
              </FormFeedback>
            )}
          </FormGroup>
        </Col>
        <Col className="px-1" md="3">
          <FormGroup>
            <Label htmlFor="username">Username</Label>
            <Input
              name="username"
              defaultValue={username}
              placeholder="Username"
              type="text"
              onChange={(e) => {
                setUsername(e.target.value);
              }}
            />
          </FormGroup>
        </Col>
      </Row>
      <Row>
        <Col className="pl-1" md="4">
          <FormGroup>
            <Label htmlFor="password">Password</Label>
            <Input
              name="password"
              placeholder="Insert password"
              type="text"
              defaultValue={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {!checkValue(passwordError) && (
              <FormFeedback className="register-form__error">
                Password is required
              </FormFeedback>
            )}
          </FormGroup>
        </Col>
        <Col className="pl-1" md="6">
          <FormGroup>
            <Label>Access token</Label>
            <Input
            defaultValue={currentUser?.access_token || ""}
              placeholder="This is generated in back-end"
              type="text"
              disabled
            />
          </FormGroup>
        </Col>
      </Row>
      <Row>
        <Col md="12">
          <FormGroup>
            <Label htmlFor="description">About Me</Label>
            <Input
              type="textarea"
              name="description"
              defaultValue={about}
              onChange={(e) => setAbout(e.target.value)}
            />
          </FormGroup>
        </Col>
      </Row>
      <Row>
        <div className="update ml-auto mr-auto">
          <Button className="btn-round" color="primary" type="submit">
            {currentUser ? "Update" : "Create"}
          </Button>
        </div>
      </Row>
    </Form>
  );
};

export default UserForm;
