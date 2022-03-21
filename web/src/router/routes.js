import Login from "../containers/login/Login";
import Registration from "../containers/registration/Registration";
import BotForm from "../pages/bots/BotForm";
import Bots from "../pages/bots/Bots";
import Dashboard from "../pages/dashboard/Dashboard";
import NotFound from "../pages/NotFound";
import TestBotForm from "../pages/paper-trading/TestBotForm";
import TestBots from "../pages/paper-trading/TestBots";
import Research from "../pages/research/Research";
import Users from "../pages/users/Users";

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
    name: "Bots",
    icon: "nc-icon nc-laptop",
    component: Bots,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/bots-create",
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
    path: "/paper-trading",
    name: "Paper trading",
    icon: "nc-icon nc-laptop",
    component: TestBots,
    layout: "/admin",
    nav: true,
    private: true,
  },
  {
    path: "/paper-trading/new/:symbol",
    name: "Create new test Bot",
    icon: "nc-icon nc-laptop",
    component: TestBotForm,
    layout: "/admin",
    nav: false,
    private: true,
  },
  {
    path: "/paper-trading/edit/:id",
    name: "Edit test Bot",
    icon: "nc-icon nc-laptop",
    component: TestBotForm,
    layout: "/admin",
    nav: false,
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
    path: "/users",
    name: "Users",
    icon: "nc-icon nc-single-02",
    component: Users,
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
  {
    path: "*",
    name: "Not found",
    component: NotFound,
    layout: "/admin",
    nav: false,
    private: true,
  },
];
export default routes;
