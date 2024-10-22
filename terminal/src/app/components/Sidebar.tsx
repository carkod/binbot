import type { FC } from "react";
import { useRef } from "react";
import { Nav } from "react-bootstrap";
import { useLocation } from "react-router";
import { NavLink } from "react-router-dom";
import { routes } from "../../App";

export const Sidebar: FC<{}> = () => {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  const activeRoute = (routeName: string) => {
    return location.pathname.indexOf(routeName) > -1 ? "active" : "";
  };

  return (
    <div className="sidebar">
      <div className="logo">
        <a
          href="/dashboard"
          className="logo__link text-decoration-none text-info"
        >
          <i className="fa-solid fa-wave-square" />
          <h1 className="logo__heading-1">Binbot</h1>
        </a>
      </div>
      <div className="sidebar-wrapper" ref={sidebarRef}>
        <Nav defaultActiveKey="/dashboard" as="ul">
          {routes.map((prop, key) => {
            if (prop.link) {
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
