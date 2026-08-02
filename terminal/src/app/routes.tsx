import React from "react";
import AutotradePage from "./pages/Autotrade";
import BotDetail from "./pages/BotDetail";
import FuturesBotDetail from "./pages/FuturesBotDetail";
import BotsPage from "./pages/Bots";
import DashboardPage from "./pages/Dashboard";
import GridLaddersPage from "./pages/GridLadders";
import GridLadderDetail from "./pages/GridLadderDetail";
import NotFound from "./pages/NotFound";
import PaperTradingPage from "./pages/PaperTradingPage";
import PaperTradingDetail from "./pages/PaperTradingDetail";
import SymbolsPage from "./pages/Symbols";
import TestAutotradePage from "./pages/TestAutotrade";
import UserFormPage from "./pages/UserForm";
import UsersPage from "./pages/Users";

export type Routes = {
  path: string;
  name?: string;
  icon?: string;
  link?: string;
  element: React.ReactNode;
  id?: string;
  nav?: boolean;
  index?: boolean;
};

export const routes: Routes[] = [
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
    path: "grid-ladders",
    link: "/grid-ladders",
    name: "Grid Ladders",
    icon: "fas fa-border-all",
    element: <GridLaddersPage />,
    id: "grid-ladders",
    nav: true,
  },
  {
    path: "grid-ladders/:id",
    link: "/grid-ladders/:id",
    name: "View Grid Ladder",
    icon: undefined,
    element: <GridLadderDetail />,
    id: "grid-ladder-detail",
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
    path: "bots/futures/new/:symbol?",
    link: "/bots/futures/new",
    icon: undefined,
    name: "New Futures Bot",
    element: <FuturesBotDetail />,
    id: "new-futures-bot",
    nav: true,
  },
  {
    path: "bots/new/:symbol?",
    link: "/bots/new",
    icon: undefined,
    name: "New Bot",
    element: <BotDetail />,
    id: "new-bot",
    nav: true,
  },
  {
    path: "bots/futures/edit/:id",
    icon: undefined,
    name: "Edit Futures Bot",
    element: <FuturesBotDetail />,
    id: "edit-futures-bot",
    nav: false,
  },
  {
    path: "bots/edit/:id",
    icon: undefined,
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
    icon: undefined,
    name: "New Test Bot",
    element: <PaperTradingDetail />,
    id: "new-test-bot",
    nav: true,
  },
  {
    path: "paper-trading/edit/:id",
    icon: undefined,
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
    path: "user",
    link: "/user",
    icon: "fas fa-user",
    name: "User",
    element: <UsersPage />,
    id: "user",
    nav: true,
  },
  {
    path: "user/new",
    link: "/user/new",
    icon: undefined,
    name: "New User",
    element: <UserFormPage mode="new" />,
    id: "new-user",
    nav: false,
  },
  {
    path: "user/edit",
    link: "/user/edit",
    icon: undefined,
    name: "Edit User",
    element: <UserFormPage mode="edit" />,
    id: "edit-user",
    nav: false,
  },
  {
    path: "*",
    element: <NotFound />,
  },
];
