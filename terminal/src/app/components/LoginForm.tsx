import React, { useEffect, type FC } from "react";
import { Button, Container, Form } from "react-bootstrap";
import { useForm, type SubmitHandler } from "react-hook-form";
import { useLocation, useNavigate } from "react-router";
import { usePostLoginMutation } from "../../features/userApiSlice";
import { getToken, setToken } from "../../utils/login";

export type LoginFormState = {
  email: string;
  password: string;
};

export const LoginForm: FC<{}> = () => {
  const [login, { data: access_token }] = usePostLoginMutation();
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const from = params.get("from") || "/";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormState>({
    mode: "onTouched",
    reValidateMode: "onSubmit",
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit: SubmitHandler<LoginFormState> = async (values) => {
    login(values);
  };

  useEffect(() => {
    const token = getToken();
    if (token || access_token) {
      if (access_token) {
        setToken(access_token);
      }
      navigate("/");
    }
  }, [navigate, from, access_token]);

  return (
    <Container className="my-4">
      <Form onSubmit={handleSubmit(onSubmit)}>
        <Form.Group className="mb-3" controlId="formBasicEmail">
          <Form.Label className="p-2">Email</Form.Label>
          <Form.Control
            className="p-2"
            type="email"
            placeholder="Enter email"
            {...register("email", {
              required: "Email is required",
              pattern: {
                value:
                  /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/,
                message: "Please enter a valid email",
              },
            })}
          />
          {errors.email && (
            <Form.Text className="text-danger">
              {errors.email.message}
            </Form.Text>
          )}
        </Form.Group>

        <Form.Group className="mb-3" controlId="formBasicPassword">
          <Form.Label className="p-2">Password</Form.Label>
          <Form.Control
            className="p-2"
            type="password"
            placeholder="Password"
            {...register("password", { required: "Password is required" })}
          />
          {errors.password && (
            <Form.Text className="text-danger">
              {errors.password.message}
            </Form.Text>
          )}
        </Form.Group>

        <Button variant="primary" type="submit">
          Submit
        </Button>
      </Form>
    </Container>
  );
};
