import Dashboard from "../pages/dashboard/Dashboard";
import TableList from "components/Tables.jsx";
import UserPage from "components/User.jsx";
import Registration from "containers/registration/Registration";

var routes = [
  {
    path: "/dashboard",
    name: "Dashboard",
    icon: "nc-icon nc-bank",
    component: Dashboard,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/bots",
    name: "Bots",
    icon: "nc-icon nc-tile-56",
    component: TableList,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/orders",
    name: "Orders",
    icon: "nc-icon nc-tile-56",
    component: TableList,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/research",
    name: "Research",
    icon: "nc-icon nc-single-02",
    component: UserPage,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/user-page",
    name: "User Profile",
    icon: "nc-icon nc-single-02",
    component: UserPage,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/registration",
    name: "Registration",
    icon: "nc-icon nc-single-02",
    component: Registration,
    layout: "/admin",
    nav: true,
    private: true
  }
];
export default routes;
