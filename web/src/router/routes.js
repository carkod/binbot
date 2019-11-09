import Dashboard from "components/Dashboard.jsx";
import Notifications from "components/Notifications.jsx";
import Icons from "components/Icons.jsx";
import TableList from "components/Tables.jsx";
import Maps from "components/Map.jsx";
import UserPage from "components/User.jsx";
import Registration from "containers/registration/Registration";
import Login from "containers/login/Login";

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
    path: "/registration",
    name: "Registration",
    icon: "nc-icon nc-single-02",
    component: Registration,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/login",
    name: "Login",
    icon: "nc-icon nc-single-02",
    component: Login,
    layout: "/login",
    nav: false,
    private: false
  },
  {
    path: "/icons",
    name: "Icons",
    icon: "nc-icon nc-diamond",
    component: Icons,
    layout: "/admin",
    nav: true,
    private: false
  },
  {
    path: "/maps",
    name: "Maps",
    icon: "nc-icon nc-pin-3",
    component: Maps,
    layout: "/admin",
    nav: true,
    private: true
  },
  {
    path: "/notifications",
    name: "Notifications",
    icon: "nc-icon nc-bell-55",
    component: Notifications,
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
    path: "/tables",
    name: "Table List",
    icon: "nc-icon nc-tile-56",
    component: TableList,
    layout: "/admin",
    nav: true,
    private: true
  },
];
export default routes;
