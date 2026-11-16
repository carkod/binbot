import {
  Box,
  Button,
  Card,
  Input,
  NativeSelect,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { type FC, useEffect } from "react";
import { type FieldValues, useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router";
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
    <Box w="100%">
      <form onSubmit={handleSubmit(saveUser)}>
        <Card mb="md" mt={16}>
          <Box mb="sm">
            <Title order={4}>
              {mode === "edit" ? "Edit User" : "Create User"}
            </Title>
          </Box>
          <Box>
            <Box w="100%">
              {mode === "edit" && !email && (
                <Text c="danger.8">Select a user to edit first.</Text>
              )}
              <SimpleGrid cols={{ base: 1, md: 3 }}>
                <Stack gap={4} mb={16}>
                  <Input.Label htmlFor="email">Email</Input.Label>
                  <TextInput
                    id="email"
                    type="email"
                    readOnly={mode === "edit"}
                    {...register("email", { required: "Email is required" })}
                    error={Boolean(errors.email)}
                  />
                  {errors.email && (
                    <Input.Error>{errors.email.message as string}</Input.Error>
                  )}
                </Stack>
                <Stack gap={4} mb={16}>
                  <Input.Label htmlFor="role">Role</Input.Label>
                  <NativeSelect id="role" {...register("role")}>
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                    <option value="customer">customer</option>
                  </NativeSelect>
                </Stack>
                <Stack gap={4} mb={16}>
                  <Input.Label htmlFor="is_active">Active?</Input.Label>
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
                </Stack>
              </SimpleGrid>
              <SimpleGrid cols={{ base: 1, md: 3 }}>
                <Stack gap={4} mb={16}>
                  <Input.Label htmlFor="full_name">Full name</Input.Label>
                  <TextInput
                    id="full_name"
                    type="text"
                    {...register("full_name")}
                  />
                </Stack>
                <Stack gap={4} mb={16}>
                  <Input.Label htmlFor="username">Username</Input.Label>
                  <TextInput
                    id="username"
                    type="text"
                    {...register("username")}
                  />
                </Stack>
                <Stack gap={4} mb={16}>
                  <Input.Label htmlFor="password">Password</Input.Label>
                  <TextInput
                    id="password"
                    type="password"
                    {...register("password", {
                      required: mode === "new" ? "Password is required" : false,
                      minLength: {
                        value: 8,
                        message: "Password must be at least 8 characters",
                      },
                      maxLength: {
                        value: 40,
                        message: "Password must be at most 40 characters",
                      },
                    })}
                    error={Boolean(errors.password)}
                  />
                  {errors.password && (
                    <Input.Error>
                      {errors.password.message as string}
                    </Input.Error>
                  )}
                </Stack>
              </SimpleGrid>
              <Stack gap={4} mb={16}>
                <Input.Label htmlFor="description">Description</Input.Label>
                <Textarea
                  id="description"
                  rows={4}
                  {...register("description")}
                />
              </Stack>
              <Box
                display="flex"
                style={{
                  gap: 8,
                }}
                component="div"
              >
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
                  onClick={() => navigate("/user")}
                  color="secondary"
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          </Box>
        </Card>
      </form>
    </Box>
  );
};

export default UserFormPage;
