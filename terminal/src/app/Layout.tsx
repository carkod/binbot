import { useEffect, useState, type FC } from "react";
import { Navigate, Outlet } from "react-router";
import { Slide, ToastContainer } from "react-toastify";
import { getToken } from "../utils/login";
import Footer from "./components/Footer";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import { useBreakpoint } from "./hooks";

export const Layout: FC<{}> = () => {
  const token = getToken();
  const breakpoint = useBreakpoint();
  // toggle sidebar
  const [expand, setExpand] = useState(breakpoint === "xs" || breakpoint === "sm");

  const handleExpand = () => {
    setExpand(!expand);
  };

  useEffect(() => {
    setExpand(expand);
  }, [breakpoint, expand]);

  if (token) {
    return (
      <div className={`wrapper ${expand && "nav-open"}`}>
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
        <Sidebar expand={expand} />
        <div className="main-panel">
          <Header onExpand={handleExpand} />
          <Outlet />
          <Footer />
        </div>
      </div>
    );
  } else {
    return <Navigate to="/login" replace />;
  }
};
