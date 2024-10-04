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
    icon: "nc-icon nc-bank",
    Component: DashboardPage,
  },
  {
    path: "bots",
    name: "Bots",
    icon: "nc-icon nc-laptop",
    Component: BotsPage,
    children: [
      {
        path: "new/:symbol?",
        name: "New Bot",
        Component: BotDetail,
      },
      {
        path: "edit/:id",
        name: "New Bot",
        Component: BotDetail,
      },
      {
        path: "autotrade",
        name: "AutoTrade",
        Component: AutotradePage,
      }
    ]
  },
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
