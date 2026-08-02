import {
  type BaseQueryApi,
  type FetchBaseQueryError,
} from "@reduxjs/toolkit/query";
import { createApi } from "@reduxjs/toolkit/query/react";
import {
  binbotBaseQuery,
  getApiErrorMessage,
  notifification,
} from "../utils/api";
import { type StandardResponse } from "../utils/api.types";
import { setToken } from "../utils/login";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponsePayload {
  email: string;
  expires: number;
  access_token: string;
}

export interface LoginResponse {
  access_token: string;
  email: string;
  token_type: string;
  error: number;
}

export type UserRole = "user" | "admin" | "customer";

export interface User {
  id?: string;
  email: string;
  is_active: boolean;
  role: UserRole;
  full_name: string;
  password?: string;
  username?: string;
  description?: string;
  created_at?: string | number;
  updated_at?: string | number;
}

export type UserPayload = Pick<
  User,
  | "email"
  | "is_active"
  | "role"
  | "full_name"
  | "password"
  | "username"
  | "description"
>;

export interface UsersResponse extends StandardResponse {
  data: User[];
}

export interface UserResponse extends StandardResponse {
  data: User;
}

const userMutationQuery = async <T>(
  args: {
    url: string;
    method: string;
    body?: unknown;
  },
  api: BaseQueryApi,
  extraOptions: unknown,
  fallbackMessage: string,
): Promise<{ data: T } | { error: FetchBaseQueryError }> => {
  const result = await binbotBaseQuery(args, api, extraOptions);

  if (result.error) {
    notifification("error", getApiErrorMessage(result.error, fallbackMessage));
    return { error: result.error };
  }

  const response = result.data as StandardResponse & { data?: T };
  if (response.error && response.error === 1) {
    notifification("error", response.message);
    const error: FetchBaseQueryError = {
      status: "CUSTOM_ERROR",
      error: response.message,
      data: response,
    };
    return {
      error,
    };
  }

  notifification("success", response.message);
  return { data: response.data as T };
};

/**
 * Root API slice
 * all other slices will be injected into this one
 * userApiSlice is the main one called since it allows
 * for login and registration other API endpoints will
 * be conditional to this. This can also allow for
 * code splitting
 */
export const userApiSlice = createApi({
  baseQuery: binbotBaseQuery,
  reducerPath: "api",
  tagTypes: ["grid-ladders", "grid-ladder", "users", "user"],
  endpoints: (build) => ({
    postLogin: build.mutation<LoginResponsePayload, FormData>({
      query: (body) => ({
        url: import.meta.env.VITE_LOGIN || "/login",
        method: "POST",
        headers: {
          "Content-Type": undefined,
        },
        body: body,
        formData: true,
      }),
      transformResponse: ({ data, message, error }) => {
        if (error && error === 1) {
          notifification("error", message);
        } else {
          notifification("success", message);
        }
        if (data.access_token) setToken(data.access_token);
        return data;
      },
      async onQueryStarted(_, { queryFulfilled }) {
        try {
          await queryFulfilled;
        } catch (error) {
          notifification("error", getApiErrorMessage(error, "Login failed"));
        }
      },
    }),
    getUsers: build.query<User[], void>({
      query: () => ({
        url: import.meta.env.VITE_USERS || "/user",
        method: "GET",
      }),
      providesTags: ["users"],
      transformResponse: ({ data, message, error }: UsersResponse) => {
        if (error && error === 1) {
          notifification("error", message);
        }
        return data;
      },
    }),
    getUser: build.query<User, string>({
      query: (email) => ({
        url: `${import.meta.env.VITE_USER || "/user"}/${encodeURIComponent(email)}`,
        method: "GET",
      }),
      providesTags: (_result, _error, email) => [{ type: "user", id: email }],
      transformResponse: ({ data, message, error }: UserResponse) => {
        if (error && error === 1) {
          notifification("error", message);
        }
        return data;
      },
    }),
    registerUser: build.mutation<User, UserPayload>({
      queryFn: (body, api, extraOptions) =>
        userMutationQuery<User>(
          {
            url: import.meta.env.VITE_REGISTER_USER || "/user/register",
            method: "POST",
            body: body,
          },
          api,
          extraOptions,
          "Create user failed",
        ),
      invalidatesTags: ["users"],
    }),
    editUser: build.mutation<User, UserPayload>({
      queryFn: (body, api, extraOptions) =>
        userMutationQuery<User>(
          {
            url: import.meta.env.VITE_USER || "/user",
            method: "PUT",
            body: body,
          },
          api,
          extraOptions,
          "Edit user failed",
        ),
      invalidatesTags: (_result, _error, body) => [
        "users",
        { type: "user", id: body.email },
      ],
    }),
    deleteUser: build.mutation<void, string>({
      queryFn: (email, api, extraOptions) =>
        userMutationQuery<void>(
          {
            url: `${import.meta.env.VITE_USER || "/user"}/${encodeURIComponent(email)}`,
            method: "DELETE",
          },
          api,
          extraOptions,
          "Delete user failed",
        ),
      invalidatesTags: ["users"],
    }),
  }),
});

export const {
  useDeleteUserMutation,
  useEditUserMutation,
  useGetUserQuery,
  usePostLoginMutation,
  useGetUsersQuery,
  useRegisterUserMutation,
} = userApiSlice;
