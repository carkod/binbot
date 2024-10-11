import type { FC } from "react"
import { Container, Navbar } from "react-bootstrap"
import { useLocation, useMatch } from "react-router"
import { Link } from "react-router-dom"
import { routes } from "../../App"

export const Header: FC<{}> = () => {

  const location = useLocation()
  const matchPath = useMatch(location.pathname)
  const loadData = matchPath ? routes.find(route => `/${route.path}` === location.pathname) : null

  return (
    <Navbar className="bg-body-tertiary">
      <Container fluid>
        <Navbar.Brand>
          <i className={`${loadData?.icon}`}></i> {loadData?.name}
        </Navbar.Brand>
        <Navbar.Collapse className="justify-content-end">
          <Navbar.Text>
            <Link to="/logout">
              <i
                className="fa-solid fa-right-from-bracket"
                style={{ color: "black" }}
              />
            </Link>
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  )
}

export default Header