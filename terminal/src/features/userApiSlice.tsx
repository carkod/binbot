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

/**
 * Root API slice
 * all other slices will be injected into this one
 * userApiSlice is the main one called since it allows
 * for login and registration other API endpoints will
 * be conditional to this. This can also allow for
 * code splitting
 */
export const userApiSlice = createApi({
  baseQuery: baseQuery,
  reducerPath: "api",
  endpoints: build => ({
    postLogin: build.mutation<LoginResponse, Partial<LoginCredentials>>({
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
