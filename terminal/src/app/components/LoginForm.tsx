import { Box, Button, Input, Stack, TextInput } from "@mantine/core";
import { useEffect, type FC } from "react";
import { useForm, type SubmitHandler } from "react-hook-form";
import { useLocation, useNavigate } from "react-router";
import { usePostLoginMutation } from "../../features/userApiSlice";
import { getToken, setToken } from "../../utils/login";

export type LoginFormState = {
  email: string;
  password: string;
};

export const LoginForm: FC<{}> = () => {
  const [login, { data: login_data }] = usePostLoginMutation();

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
    const formData = new FormData();

    formData.append("username", values.email);
    formData.append("password", values.password);
    await login(formData);
  };

  useEffect(() => {
    const token: string = getToken();

    if (token) {
      setToken(token);
      navigate("/");
    }
  }, [navigate, from, login_data]);
  return (
    <Box w="100%" my={24}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack gap={4} mb={16}>
          <Input.Label htmlFor="formBasicEmail" p={8}>
            Email
          </Input.Label>
          <TextInput
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
            id="formBasicEmail"
            p={8}
          />
          {errors.email && (
            <Input.Description c="danger.8">
              {errors.email.message}
            </Input.Description>
          )}
        </Stack>

        <Stack gap={4} mb={16}>
          <Input.Label htmlFor="formBasicPassword" p={8}>
            Password
          </Input.Label>
          <TextInput
            type="password"
            placeholder="Password"
            {...register("password", { required: "Password is required" })}
            id="formBasicPassword"
            p={8}
          />
          {errors.password && (
            <Input.Description c="danger.8">
              {errors.password.message}
            </Input.Description>
          )}
        </Stack>

        <Button type="submit" color="primary">
          Submit
        </Button>
      </form>
    </Box>
  );
};
