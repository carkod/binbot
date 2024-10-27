import { type FC } from "react";
import { Button, Container, Navbar } from "react-bootstrap";
import { useLocation, matchPath } from "react-router";
import { Link } from "react-router-dom";
import { routes } from "../../App";

export const Header: FC<{ onExpand: () => void }> = ({ onExpand }) => {
  const location = useLocation();
  const loadData = routes.find((route) => {
    const match = matchPath(route.path, location.pathname);
    if (match) {
      return route.name;
    }
    return null;
  });

  return (
    <Navbar className="bg-body-tertiary navbar-transparent navbar navbar-expand-lg">
      <Container fluid>
        <Button
          aria-expanded="true"
          type="button"
          aria-label="Toggle navigation"
          onClick={onExpand}
        >
          <span className="navbar-toggler-icon"></span>
        </Button>
        <Navbar.Brand>
          <div className="p-2 flex-fill">
            <i className={`${loadData?.icon}`}></i> {loadData?.name}
          </div>
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
  );
};

export default Header;
