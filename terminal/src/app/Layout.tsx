import type { FC } from "react"
import React from "react"
import { Navigate, Outlet } from "react-router"
import { Slide, ToastContainer } from "react-toastify"
import { getToken } from "../utils/login"
import Footer from "./components/Footer"
import Header from "./components/Header"
import Sidebar from "./components/Sidebar"

export const Layout: FC<{}> = () => {
  const mainPanel = React.useRef<HTMLDivElement>(null)
  const token = getToken()

  if (token) {
    return (
      <div>
        <div className="wrapper">
          {/* {props.loading ? (
            <Spinner color="primary" type="grow" className="c-loader" />
          ) : (
            ""
          )} */}

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
          <div className="main-panel" ref={mainPanel}>
            <Header />
            <Outlet />
            <Footer />
          </div>
        </div>
      </div>
    )
  } else {
    return <Navigate to="/login" replace />
  }
}
