import React from "react"
import type { FC } from "react"
import { Outlet } from "react-router"
import { Spinner } from "reactstrap"
import { Slide, ToastContainer } from "react-toastify"
import Header from "./components/Header"
import Sidebar from "./components/Sidebar"
import { getToken } from "../utils/login"
import LoginPage from "./pages/Login"

export const Layout: FC<{}> = () => {
	const mainPanel = React.useRef<HTMLDivElement>(null)
	const token = getToken()
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
        <LoginPage />
				{token && <>
          <Sidebar />
          <div className="main-panel" ref={mainPanel}>
          <Header />
          <Outlet />
          {/* <Footer fluid /> */}
          </div>
        </>}
        
      </div>
    </div>
  )
}
