import type { FC } from "react";
import { useRef } from "react";
import { Nav, Navbar } from "react-bootstrap";
import { useLocation } from "react-router";
import { Link, NavLink } from "react-router-dom";
import { routes } from "../../App";

export const Sidebar: FC<{ expand: boolean }> = ({ expand }) => {
  const location = useLocation();

  const activeRoute = (routeName: string) => {
    return location.pathname.indexOf(routeName) > -1 ? "active" : "";
  };

  return (
    <div className={`sidebar nav-open`}>
      <div className="logo">
        <a
          href="/dashboard"
          className="logo__link text-decoration-none text-info"
        >
          <i className="fa-solid fa-wave-square" />
          <h1 className="fs-4 ps-3">
            <Link className="btn-reset btn" to="/">Binbot</Link>
          </h1>
        </a>
      </div>
      <div className="sidebar-wrapper">
        <Nav defaultActiveKey="/dashboard" as="ul">
          {...routes.map((prop, key) => {
            if (prop.nav) {
              return (
                <Nav.Item
                  as="li"
                  className={`${!prop.icon ? "ps-5" : activeRoute(prop.path)}`}
                  key={key}
                >
                  <NavLink to={prop.link} className="nav-link">
                    <i className={prop.icon} />
                    <p>{prop.name}</p>
                  </NavLink>
                </Nav.Item>
              );
            } else {
              return null;
            }
          })}
        </Nav>
      </div>
    </div>
  );
};

export default Sidebar;
