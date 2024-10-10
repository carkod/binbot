import type { FC } from "react"
import { useAppDispatch } from "../hooks"
import { setHeaderContent } from "../../features/layoutSlice"

export const DashboardPage: FC<{}> = () => {

  const dispatch = useAppDispatch()

  dispatch(setHeaderContent({
    icon: "fas fa-robot",
    headerTitle: "Dashboard",
  }))

  return (
    <div>
      <div className="content">
        <p>Content of the dashboard</p>
      </div>
    </div>
  )
}

export default DashboardPage
