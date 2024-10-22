import { type FC } from "react";
import { Navigate, Outlet } from "react-router";
import { Slide, ToastContainer } from "react-toastify";
import { getToken } from "../utils/login";
import Footer from "./components/Footer";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";

export const Layout: FC<{}> = () => {
  const token = getToken();

  if (token) {
    return (
      <div>
        <div className="wrapper">
          <ToastContainer
            transition={Slide}
            position="top-right"
            autoClose={5000}
            hideProgressBar
            newestOnTop
            closeOnClick
            rtl={false}
            pauseOnFocusLoss={false}
            draggable={false}
            pauseOnHover
            theme="colored"
          />
          <Sidebar />
          <div className="main-panel">
            <Header />
            <Outlet />
            <Footer />
          </div>
        </div>
      </div>
    );
  } else {
    return <Navigate to="/login" replace />;
  }
};
