
import Footer from "containers/footer/Footer.jsx";
import Header from "containers/header/Header.jsx";
import Sidebar from "containers/sidebar/Sidebar";
// javascript plugin used to create scrollbars on windows
import PerfectScrollbar from "perfect-scrollbar";
import React from "react";
import { Route, Switch } from "react-router-dom";
import routes from "router/routes";


var ps;

class Dashboard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      backgroundColor: "black",
      activeColor: "info"
    };
    this.mainPanel = React.createRef();
  }
  componentDidMount() {
    if (navigator.platform.indexOf("Win") > -1) {
      ps = new PerfectScrollbar(this.mainPanel.current);
      document.body.classList.toggle("perfect-scrollbar-on");
    }
  }
  componentWillUnmount() {
    if (navigator.platform.indexOf("Win") > -1) {
      ps.destroy();
      document.body.classList.toggle("perfect-scrollbar-on");
    }
  }
  componentDidUpdate(e) {
    if (e.history.action === "PUSH") {
      this.mainPanel.current.scrollTop = 0;
      document.scrollingElement.scrollTop = 0;
    }
  }
  handleActiveClick = color => {
    this.setState({ activeColor: color });
  };
  handleBgClick = color => {
    this.setState({ backgroundColor: color });
  };
  render() {
    return (
      <div className="wrapper">
        <Sidebar
          {...this.props}
          routes={routes}
          bgColor={this.state.backgroundColor}
          activeColor={this.state.activeColor}
        />
        <div className="main-panel" ref={this.mainPanel}>
          <Header {...this.props} />
          <Switch>
            {routes.map((prop, key) => {
              return (
                <Route path={prop.layout + prop.path} component={prop.component} key={key} />
              );
            })}
          </Switch>
          <Footer fluid />
        </div>
      </div>

    );
  }
}

export default Dashboard;
