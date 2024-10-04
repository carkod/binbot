import type { FC } from "react"
import { Container, Navbar } from "react-bootstrap"
import { useAppSelector } from "../hooks"

export const Header: FC<{}> = ({}) => {
  const icon = useAppSelector(state => state.layout.icon)
  const headerTitle = useAppSelector(state => state.layout.headerTitle)

  return (
    <Navbar className="bg-body-tertiary">
      <Container>
        <Navbar.Brand>
          <i className={`${icon}`}></i> {headerTitle}
        </Navbar.Brand>
        <Navbar.Collapse className="justify-content-end">
          <Navbar.Text>
            <a href="#login">
              <i
                className="fa-solid fa-right-from-bracket"
                style={{ color: "black" }}
              />
            </a>
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  )
}

export default Header
