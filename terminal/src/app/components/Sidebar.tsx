import type { FC } from "react"
import { useRef } from "react"
import { useLocation } from "react-router"
import { useAppSelector } from "../hooks"
import { Nav } from "react-bootstrap"
import { NavLink } from "react-router-dom"

export const Sidebar: FC<{}> = () => {
  const sidebarRef = useRef<HTMLDivElement>(null)
  const location = useLocation()
  const routes = useAppSelector(state => state.routes)

  const activeRoute = (routeName: string) => {
    return location.pathname.indexOf(routeName) > -1 ? "active" : ""
  }

  const filterNavigationRoutes = () => {
    return routes.filter(r => r.nav)
  }
  return (
    <div className="sidebar">
      <div className="logo">
        <a href="/" className="logo__link">
          <i className="nc-icon nc-sound-wave logo__icon" />
          <h1 className="logo__heading-1">Binbot</h1>
        </a>
      </div>
      <div className="sidebar-wrapper" ref={sidebarRef}>
        <Nav defaultActiveKey="/dashboard" as="ul">
          {filterNavigationRoutes().map((prop, key) => (
            <Nav.Item as="li" className={activeRoute(prop.path)} key={key}>
              <Nav.Link href={prop.path}>
                <NavLink
                  to={prop.path}
                  className="nav-link"
                >
                  <i className={prop.icon} />
                  <p>{prop.name}</p>
                </NavLink>
              </Nav.Link>
            </Nav.Item>
          ))}
        </Nav>
      </div>
    </div>
  )
}

export default Sidebar
