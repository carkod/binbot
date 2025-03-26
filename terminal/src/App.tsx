import React from "react";
import { Provider } from "react-redux";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Layout } from "./app/Layout";
import AutotradePage from "./app/pages/Autotrade";
import BotDetail from "./app/pages/BotDetail";
import BotsPage from "./app/pages/Bots";
import DashboardPage from "./app/pages/Dashboard";
import LoginPage from "./app/pages/Login";
import NotFound from "./app/pages/NotFound";
import { store } from "./app/store";
import { getToken, removeToken } from "./utils/login";
import PaperTradingPage from "./app/pages/PaperTradingPage";
import PaperTradingDetail from "./app/pages/PaperTradingDetail";
import SymbolsPage from "./app/pages/Symbols";
import TestAutotradePage from "./app/pages/TestAutotrade";

export type Routes = {
  path: string;
  name?: string;
  icon?: string;
  link?: string; // Decides if shows on Sidebar
  element: React.FC;
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
  {
    path: "paper-trading",
    link: "/paper-trading",
    name: "Paper Trading",
    icon: "fas fa-pencil-ruler",
    element: <PaperTradingPage />,
    id: "paper-trading",
    nav: true,
  },
  {
    path: "paper-trading/new/:symbol?",
    link: "/paper-trading/new",
    icon: null,
    name: "New Test Bot",
    element: <PaperTradingDetail />,
    id: "new-test-bot",
    nav: true,
  },
  {
    path: "paper-trading/edit/:id",
    icon: null,
    name: "Edit Test Bot",
    element: <PaperTradingDetail />,
    id: "edit-test-bot",
    nav: false,
  },
  {
    path: "test-autotrade",
    link: "/test-autotrade",
    icon: "fas fa-chart-simple",
    name: "Test Autotrade",
    element: <TestAutotradePage />,
    id: "test-autotrade",
    nav: true,
  },
  {
    path: "symbols",
    link: "/symbols",
    icon: "fas fa-ban",
    name: "symbols",
    element: <SymbolsPage />,
    id: "symbols",
    nav: true,
  },
  {
    path: "*",
    element: <NotFound />,
  },
];

const rootRouter = createBrowserRouter(
  [
    {
      path: "/login",
      Component: () => {
        const token = getToken();
        if (token) {
          return <Navigate to="/" replace />;
        } else {
          return <LoginPage />;
        }
      },
    },
    {
      id: "root",
      path: "/",
      element: <Layout />,
      hydrateFallbackElement: <div>Loading...</div>,
      children: routes,
    },
    {
      path: "/logout",
      Component: () => {
        removeToken();
        return <Navigate to="/login" replace />;
      },
    },
  ],
  {
    future: {
      v7_partialHydration: true,
      v7_fetcherPersist: true,
      v7_normalizeFormMethod: true,
      v7_skipActionErrorRevalidation: true,
    },
  },
);

export const App = () => {
  return (
    <Provider store={store}>
      <RouterProvider
        router={rootRouter}
        future={{
          v7_startTransition: false,
        }}
      />
    </Provider>
  );
};

export default App;
