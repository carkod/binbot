import Dashboard from "../pages/dashboard/Dashboard";
import UserPage from "../components/User.jsx";
import Registration from "../containers/registration/Registration";
import BotForm from "../pages/bots/BotForm";
import Bots from "../pages/bots/Bots";
import Orders from "../pages/orders/Orders";
import Research from "../pages/research/Research";
import Login from "../containers/login/Login";

const routes = [
  {
    path: "/login",
    name: "Login",
    icon: null,
    component: Login,
    layout: null,
    nav: false,
    private: false,
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    icon: "nc-icon nc-bank",
    component: Dashboard,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/bots",
    exact: true,
    name: "Bots",
    icon: "nc-icon nc-laptop",
    component: Bots,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/bots-create",
    exact: true,
    name: "Create new Bot",
    icon: "nc-icon nc-laptop",
    component: BotForm,
    layout: "/admin",
    nav: false,
    private: true,
  },
  {
    path: "/bots-edit/:id",
    name: "Edit Bot",
    icon: "nc-icon nc-laptop",
    component: BotForm,
    layout: "/admin",
    nav: false,
    private: true,
  },
  {
    path: "/orders",
    name: "Orders",
    icon: "nc-icon nc-briefcase-24",
    component: Orders,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/research",
    name: "Research",
    icon: "nc-icon nc-ruler-pencil",
    component: Research,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/user-page",
    name: "User Profile",
    icon: "nc-icon nc-single-02",
    component: UserPage,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/registration",
    name: "Registration",
    icon: "nc-icon nc-single-02",
    component: Registration,
    layout: "/admin",
    nav: true,
    private: true,
  },
];
export default routes;
