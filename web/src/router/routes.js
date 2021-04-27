import UserPage from "../components/User.jsx";
import Registration from "../containers/registration/Registration";
import BotForm from "../pages/bots/BotForm";
import Bots from "../pages/bots/Bots";
import Orders from "../pages/orders/Orders";
import Dashboard from "../pages/dashboard/Dashboard";

var routes = [
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
    icon: "nc-icon nc-tile-56",
    component: Bots,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/bots-create",
    exact: true,
    name: "Create new Bot",
    icon: "nc-icon nc-tile-56",
    component: BotForm,
    layout: "/admin",
    nav: false,
    private: true,
  },
  {
    path: "/bots-edit/:id",
    name: "Edit Bot",
    icon: "nc-icon nc-tile-56",
    component: BotForm,
    layout: "/admin",
    nav: false,
    private: true,
  },
  {
    path: "/orders",
    name: "Orders",
    icon: "nc-icon nc-tile-56",
    component: Orders,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/research",
    name: "Research",
    icon: "nc-icon nc-single-02",
    component: UserPage,
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
