import { createApi } from "@reduxjs/toolkit/query/react"
import {
  binbotBaseQuery,
  notifification,
} from "../utils/api"

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
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
  baseQuery: binbotBaseQuery,
  reducerPath: "api",
  endpoints: build => ({
    postLogin: build.mutation<LoginResponse, Partial<LoginCredentials>>({
      query: body => ({
          url: import.meta.env.VITE_LOGIN || "/login",
          method: "POST",
          body: body,
      }),
      transformResponse: ({ data }) => {
        if (data.error === 1) {
          notifification("error", data.message)
        }
        return data
      }
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
      }),
    }),
  }),
})

export const {
  usePostLoginMutation,
  useGetUsersQuery,
  useRegisterUserMutation,
} = userApiSlice
