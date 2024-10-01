import { Provider } from "react-redux"
import { createBrowserRouter, redirect, RouterProvider } from "react-router-dom"
import { Layout } from "./app/Layout"
import BotsPage from "./app/pages/Bots"
import DashboardPage from "./app/pages/Dashboard"
import LoginPage from "./app/pages/Login"
import {
  loginAction,
  loginLoader
} from "./app/routes/auth"
import { store } from "./app/store"
import { getToken, removeToken } from "./utils/login"

const routes = [
  {
    path: "login",
    name: "Login",
    icon: null,
    Component: LoginPage,
    index: true,
    action: loginAction,
    loader: loginLoader,
  },
  {
    path: "dashboard",
    name: "Dashboard",
    icon: null,
    Component: DashboardPage,
    // loader: protectedLoader,
  },
  {
    path: "bots",
    name: "Bots",
    icon: null,
    Component: BotsPage,
    // loader: protectedLoader,
  },
]

const rootRouter = createBrowserRouter([
  {
    id: "root",
    path: "/",
    loader() {
      const token = getToken()
      if (token) {
        return {
          token: token
        }
      } else {
        return {
          token: null
        }
      }
    },
    Component: Layout,
    children: routes,
  },
  {
    path: "/logout",
    async action() {
      removeToken()
      return redirect("/login")
    },
  },
])

export const App = () => {
  return (
    <Provider store={store}>
      <RouterProvider
        router={rootRouter}
        fallbackElement={<p>Initial Load...</p>}
      />
    </Provider>
  )
}

export default App
