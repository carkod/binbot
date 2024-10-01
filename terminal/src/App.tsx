import { RouterProvider } from "react-router-dom"
import { createBrowserRouter, redirect } from "react-router-dom"
import LoginPage from "./app/pages/Login"
import { loginAction, loginLoader, protectedLoader } from "./app/routes"
import DashboardPage from "./app/pages/Dashboard"
import { Layout } from "./app/Layout"
import BotsPage from "./app/pages/Bots"
import { getToken, removeToken } from "./utils/login"
import { Provider } from "react-redux"
import { store } from "./app/store"

const routes = [
  {
    path: "login",
    name: "Login",
    icon: null,
    Component: LoginPage,
    index: true,
    // action: loginAction,
    // loader: loginLoader,
  },
  {
    path: "dashboard",
    name: "Dashboard",
    icon: null,
    Component: DashboardPage,
    loader: protectedLoader,
  },
  {
    path: "bots",
    name: "Bots",
    icon: null,
    Component: BotsPage,
    loader: protectedLoader,
  },
]

const rootRouter = createBrowserRouter([
  {
    id: "root",
    path: "/",
    loader() {
      const token = getToken()
      if (token) {
        return token
      } else {
        return null
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
