import { Provider } from "react-redux"
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom"
import { Layout } from "./app/Layout"
import BotsPage from "./app/pages/Bots"
import DashboardPage from "./app/pages/Dashboard"
import LoginPage from "./app/pages/Login"
import { store } from "./app/store"
import BotDetail from "./app/pages/BotDetail"
import AutotradePage from "./app/pages/Autotrade"

export const routes = [
  {
    path: "dashboard",
    name: "Dashboard",
    icon: "fas fa-chart-simple",
    Component: DashboardPage,
  },
  {
    path: "bots",
    name: "Bots",
    icon: "fas fa-robot",
    Component: BotsPage,
  },
  {
    path: "bots/new/:symbol?",
    icon: null,
    name: "New Bot",
    element: <BotDetail />,
  },
  {
    path: "bots/edit/:id",
    icon: null,
    name: "Edit Bot",
    element: <BotDetail />,
  },
  {
    path: "autotrade",
    icon: "fas fa-chart-simple",
    name: "AutoTrade",
    Component: AutotradePage,
  }
]

const rootRouter = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    id: "root",
    path: "/",
    element: <Layout />,
    children: routes,
  },
  {
    path: "/logout",
    element: <Navigate to="/login" replace />,
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
