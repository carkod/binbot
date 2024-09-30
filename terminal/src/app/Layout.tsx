import React from "react"
import type { FC } from "react"
import { Outlet } from "react-router"
import { Spinner } from "reactstrap"
import 'react-redux-toastr/lib/css/react-redux-toastr.min.css'
import { Slide, ToastContainer } from "react-toastify"
import Header from "./components/Header"
import Sidebar from "./components/Sidebar"
import { getToken } from "../utils/login"

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
				{token && <Sidebar />}
        <div className="main-panel" ref={mainPanel}>
          <Header />
          <Outlet />
          {/* <Footer fluid /> */}
        </div>
      </div>
    </div>
  )
}
