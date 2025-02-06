import React, { createContext, useState, type FC } from "react";
import { Navigate, Outlet } from "react-router";
import { Slide, ToastContainer } from "react-toastify";
import { getToken } from "../utils/login";
import Footer from "./components/Footer";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import { useBreakpoint } from "./hooks";

export const SpinnerContext = createContext({
  spinner: false,
  setSpinner: (value: boolean) => {},
});

export const Layout: FC<{}> = () => {
  const token = getToken();
  const breakpoint = useBreakpoint();
  const [spinner, setSpinner] = useState(false);
  const spinnerValue = { spinner, setSpinner };

  // toggle sidebar by default on larger screens
  // collapse sidebar by default on smaller screens
  const [expand, setExpand] = useState(
    breakpoint === "md" || breakpoint === "lg" || breakpoint === "xl"
  );

  const handleExpand = () => {
    setExpand(!expand);
  };

  if (token) {
    return (
      <div className={`wrapper ${expand ? "nav-open" : ""}`}>
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
          {spinner && (
            <div
              className="d-flex align-items-center justify-content-center"
              style={{
                position: "absolute",
                zIndex: 99,
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: "rgba(0, 0, 0, 0.5)",
              }}
            >
              <div className="spinner-border text-warning" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          )}

          <SpinnerContext.Provider value={spinnerValue}>
            <Header onExpand={handleExpand} />
            <Outlet />
            <Footer />
          </SpinnerContext.Provider>
        </div>
      </div>
    );
  } else {
    return <Navigate to="/login" replace />;
  }
};
