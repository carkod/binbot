import { type FC } from "react"
import { setHeaderContent } from "../../features/layoutSlice"
import { useAppDispatch } from "../hooks"

export const AutotradePage: FC<{}> = () => {
  const dispatch = useAppDispatch()

  dispatch(setHeaderContent({
    icon: "fas fa-robot",
    headerTitle: "Autotrade",
  }))

  return (
    <div>
      <div className="content">
        <p>Autotrade</p>
      </div>
    </div>
  )
}

export default AutotradePage
