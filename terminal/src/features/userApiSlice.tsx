import { createApi } from "@reduxjs/toolkit/query/react"
import {
  baseQuery,
} from "../utils/api"

interface LoginCredentials {
  email: string
  password: string
}

interface LoginResponse {
  access_token: string
  email: string
  token_type: string
  error: number
}

// Define a service using a base URL and expected endpoints
export const userApiSlice = createApi({
  baseQuery: baseQuery,
  reducerPath: "loginApi",
  // Tag types are used for caching and invalidation.
  tagTypes: ["login"],
  endpoints: build => ({
    postLogin: build.mutation<LoginResponse, LoginCredentials>({
      query: body => ({
          url: import.meta.env.VITE_LOGIN || "/login",
          method: "POST",
          body: body,
          invalidatesTags: ["login"]
      }),
    }),
    getUsers: build.query<LoginResponse, void>({
      query: () => ({
        url: import.meta.env.VITE_USERS || "/users",
        method: "GET",
      }),
    }),
    registerUser: build.mutation<LoginCredentials, Partial<LoginResponse>>({
      query: body => ({
        url: import.meta.env.VITE_REGISTER_USER || "/user/register",
        method: "POST",
        body: body,
        invalidatesTags: ["login"],
      }),
    }),
  }),
})

export const {
  usePostLoginMutation,
  useGetUsersQuery,
  useRegisterUserMutation,
} = userApiSlice
