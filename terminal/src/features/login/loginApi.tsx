// Need to use the React-specific entry point to import `createApi`
import { createApi } from "@reduxjs/toolkit/query/react"
import {
  baseQuery,
  defaultResponseHandler,
  defaultStatusValidator,
} from "../../utils/api"

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
  tagTypes: ["Login"],
  endpoints: build => ({
    postLogin: build.mutation<LoginResponse, LoginCredentials>({
      query: body => {
        console.log("body", JSON.stringify(body))
        return {
          url: import.meta.env.VITE_LOGIN || "/login",
          method: "POST",
          body: body,
          responseHandler: defaultResponseHandler,
          validateStatus: defaultStatusValidator,
          invalidatesTags: ["Login"]
        }
      },
    }),
    getUsers: build.query<LoginResponse, void>({
      query: () => ({
        url: import.meta.env.VITE_USERS || "/users",
        method: "GET",
        responseHandler: defaultResponseHandler,
        validateStatus: defaultStatusValidator,
      }),
    }),
    registerUser: build.mutation<LoginCredentials, Partial<LoginResponse>>({
      query: body => ({
        url: import.meta.env.VITE_REGISTER_USER || "/user/register",
        method: "POST",
        body: body,
        responseHandler: defaultResponseHandler,
        validateStatus: defaultStatusValidator,
        invalidatesTags: ["Login"],
      }),
    }),
  }),
})

export const {
  usePostLoginMutation,
  useGetUsersQuery,
  useRegisterUserMutation,
} = userApiSlice
