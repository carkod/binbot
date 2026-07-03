import { Provider } from "react-redux";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import { Layout } from "./app/Layout";
import LoginPage from "./app/pages/Login";
import { store } from "./app/store";
import { getToken, removeToken } from "./utils/login";
import { SymbolProvider } from "./app/providers/SymbolProvider";
import { routes } from "./app/routes";

const rootRouter = createBrowserRouter([
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
    element: (
      <SymbolProvider>
        <Layout />
      </SymbolProvider>
    ),
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
]);

export const App = () => {
  return (
    <Provider store={store}>
      <RouterProvider router={rootRouter} />
    </Provider>
  );
};

export default App;
