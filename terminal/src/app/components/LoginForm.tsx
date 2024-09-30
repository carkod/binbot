import { useState } from "react";
import type { FC } from "react";
import { useActionData } from "react-router";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Form,
  FormFeedback,
  FormGroup,
  Input,
  Row,
} from "reactstrap";

interface LoginFormProps {
	handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void
}

interface LoginFormState {
	email: string
	password: string
}

export const LoginForm: FC<LoginFormProps> = ({ handleSubmit }) => {

  const error = useActionData() as { error: string } | undefined
  
  const [formData, setFormData] = useState<LoginFormState>({
    email: "",
    password: "",
  });

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  return (
    <div className="c-login-card">
      <Card className="card-user">
        <CardHeader>
          <CardTitle tag="h3">Login</CardTitle>
        </CardHeader>
        <CardBody>
          <Form onSubmit={handleSubmit}>
            <Row>
              <Col md="12">
                <FormGroup>
                  <label htmlFor="email">Email address</label>
                  <Input
                    // invalid={emailIsRequiredError}
                    placeholder="Email"
                    type="email"
                    name="email"
                    onChange={handleChange}
                  />
                  {error ? (
                    <FormFeedback>Email is required</FormFeedback>
                ) : null}
                  
                </FormGroup>
              </Col>
              <Col md="12">
                <FormGroup>
                  <label htmlFor="password">Password</label>
                  <Input
                    // invalid={passwordIsRequiredError}
                    type="password"
                    name="password"
                    onChange={handleChange}
                  />
                  {error ? (
                    <FormFeedback className="register-form__error">
                      Password is required
                    </FormFeedback>
                  ) : null}
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
  )
}
