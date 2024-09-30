import React from "react"
import type { FC } from "react"

export const Sidebar: FC<{}> = () => {
  return (
    <div>
      <div className="content">
        <h1>Sidebar</h1>
        <p>Content of the dashboard</p>
      </div>
    </div>
  )
}

export default Sidebar
