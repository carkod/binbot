import React from "react"
import type { FC } from "react"

export const Header: FC<{}> = () => {
  return (
    <div>
      <div className="content">
        <h1>Header</h1>
        <p>Content of the header</p>
      </div>
    </div>
  )
}

export default Header
