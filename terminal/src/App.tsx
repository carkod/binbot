import { RouterProvider } from "react-router-dom"
import "./App.css"
import { createBrowserRouter, redirect } from "react-router-dom"
import LoginPage from "./app/pages/Login"
import { loginAction, loginLoader } from "./app/routes"
import DashboardPage from "./app/pages/Dashboard"
import { Layout } from "./app/Layout"
import BotsPage from "./app/pages/Bots"


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
    private: true,
    // loader: loginLoader,
  },
  {
    path: "bots",
    name: "Bots",
    icon: null,
    Component: BotsPage,
    private: true,
    // loader: loginLoader,
  },
]

const rootRouter = createBrowserRouter([
  {
    id: "root",
    path: "/",
    loader() {
      // Our root route always provides the user, if logged in
      return { loggedIn: true }
    },
    Component: Layout,
    children: routes,
  },
  // {
  //   path: "/logout",
  //   async action() {
  //     // We signout in a "resource route" that we can hit from a fetcher.Form
  //     await fakeAuthProvider.signout()
  //     return redirect("/")
  //   },
  // },
])

export const App = () => {
  return (
    <RouterProvider router={rootRouter} fallbackElement={<p>Initial Load...</p>} />
  )
}

export default App
