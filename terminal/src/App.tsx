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
import BlacklistPage from "./app/pages/BlacklistPage";
import NotFound from './app/pages/NotFound';
import { store } from "./app/store";
import { getToken, removeToken } from './utils/login';
import PaperTradingPage from "./app/pages/PaperTradingPage";
import PaperTradingDetail from "./app/pages/PaperTradingDetail";

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
    path: "blacklist",
    link: "/blacklist",
    icon: "fas fa-ban",
    name: "Blacklist",
    element: <BlacklistPage />,
    id: "blacklist",
    nav: true,
  },
  {
    path: "*",
    element: <NotFound />,
  }
];

const rootRouter = createBrowserRouter([
  {
    path: "/login",
    Component: () => {
      const token = getToken();
      if (token) {
        return <Navigate to="/" replace />
      } else {
        return <LoginPage />;
      }
    },
  },
  {
    id: "root",
    path: "/",
    element: <Layout />,
    children: routes,
  },
  {
    path: "/logout",
    Component: () => {
      removeToken();
      return <Navigate to="/login" replace />
    },
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
