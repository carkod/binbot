import { Provider } from "react-redux"
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom"
import { Layout } from "./app/Layout"
import BotsPage from "./app/pages/Bots"
import DashboardPage from "./app/pages/Dashboard"
import LoginPage from "./app/pages/Login"
import { store } from "./app/store"
import BotDetail from "./app/pages/BotDetail"
import AutotradePage from "./app/pages/Autotrade"

export type Routes = {
  path: string
  name?: string
  icon?: string
  link?: string  // Decides if shows on Sidebar
  element: JSX.Element
  id: string  // Unique name to match path
}

export const routes = [
  {
    index: true,
    path: "dashboard",
    link: "/dashboard",
    name: "Dashboard",
    icon: "fas fa-chart-simple",
    element: <DashboardPage />,
    id: "dashboard",
  },
  {
    path: "bots",
    link: "/bots",
    name: "Bots",
    icon: "fas fa-robot",
    element: <BotsPage />,
    id: "bots",
  },
  {
    path: "bots/new/:symbol?",
    link: "/bots/new",
    icon: null,
    name: "New Bot",
    element: <BotDetail />,
    id: "new-bot",
  },
  {
    path: "bots/edit/:id",
    icon: null,
    name: "Edit Bot",
    element: <BotDetail />,
    id: "edit-bot",
  },
  {
    path: "autotrade",
    link: "/autotrade",
    icon: "fas fa-chart-simple",
    name: "AutoTrade",
    element: <AutotradePage />,
    id: "autotrade",
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
