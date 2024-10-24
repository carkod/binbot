import React from 'react';
import { Provider } from "react-redux";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Layout } from "./app/Layout";
import BotsPage from "./app/pages/Bots";
import DashboardPage from "./app/pages/Dashboard";
import LoginPage from "./app/pages/Login";
import { store } from "./app/store";
import BotDetail from "./app/pages/BotDetail";
import AutotradePage from "./app/pages/Autotrade";

export type Routes = {
  path: string;
  name?: string;
  icon?: string;
  link?: string; // Decides if shows on Sidebar
  element: JSX.Element;
  id: string; // Unique name to match path
};

export const routes = [
  {
    index: true,
    path: "/",
    link: "/",
    name: "Home",
    icon: "fas fa-chart-simple",
    element: <DashboardPage />,
    id: "dashboard",
    nav: false,
  },
  {
    path: "bots",
    link: "/bots",
    name: "Bots",
    icon: "fas fa-robot",
    element: <BotsPage />,
    id: "bots",
    nav: true,
  },
  {
    path: "bots/new/:symbol?",
    link: "/bots/new",
    icon: null,
    name: "New Bot",
    element: <BotDetail />,
    id: "new-bot",
    nav: true,
  },
  {
    path: "bots/edit/:id",
    icon: null,
    name: "Edit Bot",
    element: <BotDetail />,
    id: "edit-bot",
    nav: false,
  },
  {
    path: "autotrade",
    link: "/autotrade",
    icon: "fas fa-chart-simple",
    name: "Autotrade",
    element: <AutotradePage />,
    id: "autotrade",
    nav: true,
  },
];

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
]);

export const App = () => {
  return (
    <Provider store={store}>
      <RouterProvider
        router={rootRouter}
        fallbackElement={<p>Initial Load...</p>}
      />
    </Provider>
  );
};

export default App;
