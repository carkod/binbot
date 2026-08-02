import { type FC, useEffect } from "react";
import { Button, Card, Col, Container, Form, Row } from "react-bootstrap";
import { useForm, type FieldValues } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  type UserPayload,
  useEditUserMutation,
  useGetUserQuery,
  useRegisterUserMutation,
} from "../../features/userApiSlice";
import LightSwitch from "../components/LightSwitch";

const defaultValues: UserPayload = {
  email: "",
  is_active: true,
  role: "user",
  full_name: "",
  password: "",
  username: "",
  description: "",
};

type UserFormPageProps = {
  mode: "new" | "edit";
};

const UserFormPage: FC<UserFormPageProps> = ({ mode }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const email = searchParams.get("email") || "";
  const [registerUser, { isLoading: isCreating }] = useRegisterUserMutation();
  const [editUser, { isLoading: isEditing }] = useEditUserMutation();
  const { data: user, isFetching } = useGetUserQuery(email, {
    skip: mode !== "edit" || !email,
  });

  const {
    register,
    setValue,
    reset,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FieldValues>({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues,
  });

  const isActive = watch("is_active", defaultValues.is_active);

  useEffect(() => {
    if (mode === "new") {
      reset(defaultValues);
    }
  }, [mode, reset]);

  useEffect(() => {
    if (user) {
      reset({
        email: user.email,
        is_active: user.is_active,
        role: user.role,
        full_name: user.full_name,
        password: user.password || "",
        username: user.username || "",
        description: user.description || "",
      });
    }
  }, [reset, user]);

  const saveUser = async (formData: FieldValues) => {
    const payload: UserPayload = {
      email: formData.email,
      is_active: Boolean(formData.is_active),
      role: formData.role,
      full_name: formData.full_name,
      password: formData.password,
      username: formData.username,
      description: formData.description,
    };

    if (mode === "edit" && !payload.password) {
      delete payload.password;
    }

    if (mode === "edit") {
      await editUser(payload).unwrap();
    } else {
      await registerUser(payload).unwrap();
    }

    navigate("/user");
  };

  return (
    <Container>
      <Form onSubmit={handleSubmit(saveUser)}>
        <Card className="mt-3">
          <Card.Header>
            <Row className="align-items-center">
              <Col>
                <Card.Title>
                  {mode === "edit" ? "Edit User" : "Create User"}
                </Card.Title>
              </Col>
            </Row>
          </Card.Header>
          <Card.Body>
            <Container>
              {mode === "edit" && !email && (
                <p className="text-danger">Select a user to edit first.</p>
              )}
              <Row>
                <Col md="4">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="email">Email</Form.Label>
                    <Form.Control
                      id="email"
                      type="email"
                      isInvalid={Boolean(errors.email)}
                      readOnly={mode === "edit"}
                      {...register("email", { required: "Email is required" })}
                    />
                    {errors.email && (
                      <Form.Control.Feedback type="invalid">
                        {errors.email.message as string}
                      </Form.Control.Feedback>
                    )}
                  </Form.Group>
                </Col>
                <Col md="4">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="role">Role</Form.Label>
                    <Form.Select id="role" {...register("role")}>
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                      <option value="customer">customer</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md="4">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="is_active">Active?</Form.Label>
                    <br />
                    <LightSwitch
                      value={Boolean(isActive)}
                      name="is_active"
                      register={register}
                      toggle={(name, value) => {
                        setValue(name, !value, {
                          shouldDirty: true,
                          shouldValidate: true,
                        });
                      }}
                    />
                  </Form.Group>
                </Col>
              </Row>
              <Row>
                <Col md="4">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="full_name">Full name</Form.Label>
                    <Form.Control
                      id="full_name"
                      type="text"
                      {...register("full_name")}
                    />
                  </Form.Group>
                </Col>
                <Col md="4">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="username">Username</Form.Label>
                    <Form.Control
                      id="username"
                      type="text"
                      {...register("username")}
                    />
                  </Form.Group>
                </Col>
                <Col md="4">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="password">Password</Form.Label>
                    <Form.Control
                      id="password"
                      type="password"
                      isInvalid={Boolean(errors.password)}
                      {...register("password", {
                        required:
                          mode === "new" ? "Password is required" : false,
                        minLength: {
                          value: 8,
                          message: "Password must be at least 8 characters",
                        },
                        maxLength: {
                          value: 40,
                          message: "Password must be at most 40 characters",
                        },
                      })}
                    />
                    {errors.password && (
                      <Form.Control.Feedback type="invalid">
                        {errors.password.message as string}
                      </Form.Control.Feedback>
                    )}
                  </Form.Group>
                </Col>
              </Row>
              <Row>
                <Col md="12">
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="description">Description</Form.Label>
                    <Form.Control
                      id="description"
                      as="textarea"
                      rows={4}
                      {...register("description")}
                    />
                  </Form.Group>
                </Col>
              </Row>
              <Row>
                <Col md="12">
                  <div className="d-flex gap-2">
                    <Button
                      type="submit"
                      disabled={
                        isCreating ||
                        isEditing ||
                        isFetching ||
                        (mode === "edit" && !email)
                      }
                    >
                      {mode === "edit" ? "Save User" : "Create User"}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => navigate("/user")}
                    >
                      Cancel
                    </Button>
                  </div>
                </Col>
              </Row>
            </Container>
          </Card.Body>
        </Card>
      </Form>
    </Container>
  );
};

export default UserFormPage;
