import React from "react";
import { Link, withRouter } from "react-router-dom";
import {
  Button,
  Collapse,
  Input,
  InputGroup,
  InputGroupText,
  Nav,
  Navbar,
  NavbarBrand,
  NavbarToggler,
  NavItem,
} from "reactstrap";
import { removeToken } from "../../request";
import routes from "../../router/routes";

class Header extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      isOpen: false,
      dropdownOpen: false,
      color: "transparent",
    };
    this.toggle = this.toggle.bind(this);
    this.dropdownToggle = this.dropdownToggle.bind(this);
    this.sidebarToggle = React.createRef();
    this.handleLogout = this.handleLogout.bind(this);
  }
  toggle() {
    if (this.state.isOpen) {
      this.setState({
        color: "transparent",
      });
    } else {
      this.setState({
        color: "dark",
      });
    }
    this.setState({
      isOpen: !this.state.isOpen,
    });
  }
  dropdownToggle(e) {
    this.setState({
      dropdownOpen: !this.state.dropdownOpen,
    });
  }
  getBrand() {
    let brandName = "Page not found";
    routes.map((prop, key) => {
      if (window.location.href.indexOf(prop.layout + prop.path) !== -1) {
        brandName = prop.name;
      }
      return null;
    });
    return brandName;
  }
  openSidebar() {
    document.documentElement.classList.toggle("nav-open");
    this.sidebarToggle.current.classList.toggle("toggled");
  }
  // function that adds color dark/transparent to the navbar on resize (this is for the collapse)
  updateColor() {
    if (window.innerWidth < 993 && this.state.isOpen) {
      this.setState({
        color: "dark",
      });
    } else {
      this.setState({
        color: "transparent",
      });
    }
  }
  componentDidMount() {
    window.addEventListener("resize", this.updateColor.bind(this));
  }
  componentDidUpdate(e) {
    if (
      window.innerWidth < 993 &&
      e.history.location.pathname !== e.location.pathname &&
      document.documentElement.className.indexOf("nav-open") !== -1
    ) {
      document.documentElement.classList.toggle("nav-open");
      this.sidebarToggle.current.classList.toggle("toggled");
    }
  }

  handleLogout(e) {
    e.preventDefault();
    removeToken();
    this.props.history.push("/login");
  }
  render() {
    return (
      // add or remove classes depending if we are on full-screen-maps page or not
      <Navbar
        expand="lg"
        className={
          this.state.color === "transparent" ? "navbar-transparent " : ""
        }
      >
        <div className="navbar-wrapper">
          <div className="navbar-toggle">
            <button
              type="button"
              ref={this.sidebarToggle}
              className="navbar-toggler"
              onClick={() => this.openSidebar()}
            >
              <span className="navbar-toggler-bar bar1" />
              <span className="navbar-toggler-bar bar2" />
              <span className="navbar-toggler-bar bar3" />
            </button>
          </div>
          <NavbarBrand href="/">{this.getBrand()}</NavbarBrand>
          <div className="navbar-content">
            {this.props.location.pathname.includes("/admin/bots") && (
              <Link to="/admin/bots-create">
                <Button className="btn btn-link">New bot</Button>
              </Link>
            )}
            {this.props.location.pathname.includes("/admin/paper-trading") && (
                <Button className="btn btn-link" onClick={() => window.location.href = "/admin/paper-trading/new"}>New bot</Button>
            )}
          </div>
        </div>
        <NavbarToggler onClick={this.toggle}>
          <span className="navbar-toggler-bar navbar-kebab" />
          <span className="navbar-toggler-bar navbar-kebab" />
          <span className="navbar-toggler-bar navbar-kebab" />
        </NavbarToggler>
        <Collapse
          isOpen={this.state.isOpen}
          navbar
          className="justify-content-end"
        >
          <form>
            <InputGroup className="no-border">
              <Input placeholder="Search..." />
              <InputGroupText>
                <i className="nc-icon nc-zoom-split" />
              </InputGroupText>
            </InputGroup>
          </form>
          <Nav navbar>
            <NavItem>
              <button className="btn-reset nav-link btn-magnify">
                <i className="nc-icon nc-layout-11" />
                <p>
                  <span className="d-lg-none d-md-block">Stats</span>
                </p>
              </button>
            </NavItem>
            <NavItem>
              <button
                onClick={this.handleLogout}
                className="btn-reset nav-link btn-rotate"
              >
                <i className="nc-icon nc-user-run" />
                <p>
                  <span className="d-lg-none d-md-block">Account</span>
                </p>
              </button>
            </NavItem>
          </Nav>
        </Collapse>
      </Navbar>
    );
  }
}

export default withRouter(Header);
