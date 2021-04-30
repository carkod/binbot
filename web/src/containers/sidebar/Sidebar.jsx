import React, { Component } from "react";
import { NavLink } from "react-router-dom";
import { Nav } from "reactstrap";
class Sidebar extends Component {
  constructor(props) {
    super(props);
    this.sidebar = React.createRef();
  }
  // verifies if routeName is the one active (in browser input)
  activeRoute(routeName) {
    if (this.props.location) {
      return this.props.location.pathname.indexOf(routeName) > -1
        ? "active"
        : "";
    } else {
      return "";
    }
  }

  filterNavigationRoutes() {
    const { routes } = this.props;
    const navigation = routes.filter((r) => r.nav);
    return navigation;
  }

  render() {
    return (
      <div
        className="sidebar"
        data-color={this.props.bgColor}
        data-active-color={this.props.activeColor}
      >
        <div className="logo">
          <a href="/" className="logo__link">
            <i className="nc-icon nc-sound-wave logo__icon" />
            <h1 className="logo__heading-1">Binbot</h1>
          </a>
        </div>
        <div className="sidebar-wrapper" ref={this.sidebar}>
          <Nav>
            {this.filterNavigationRoutes().map((prop, key) => {
              return (
                <li
                  className={
                    this.activeRoute(prop.path) +
                    (prop.pro ? " active-pro" : "")
                  }
                  key={key}
                >
                  <NavLink
                    to={prop.layout + prop.path}
                    className="nav-link"
                    activeClassName="active"
                  >
                    <i className={prop.icon} />
                    <p>{prop.name}</p>
                  </NavLink>
                </li>
              );
            })}
          </Nav>
        </div>
      </div>
    );
  }
}

export default Sidebar;
