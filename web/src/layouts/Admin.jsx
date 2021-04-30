import React from "react";
import { connect } from "react-redux";
import ReduxToastr from "react-redux-toastr";
import { Route, Switch } from "react-router-dom";
import { Spinner } from "reactstrap";
import Footer from "../containers/footer/Footer.jsx";
import Header from "../containers/header/Header.jsx";
import Sidebar from "../containers/sidebar/Sidebar";
import routes from "../router/routes";
import { checkValue } from "../validations.js";
class Admin extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      backgroundColor: "black",
      activeColor: "info",
      loading: false,
    };
    this.mainPanel = React.createRef();
  }
  componentDidUpdate = (p) => {
    if (this.props.loading !== p.loading) {
      this.setState({ loading: this.props.loading})
    }
  }
  handleActiveClick = (color) => {
    this.setState({ activeColor: color });
  };
  handleBgClick = (color) => {
    this.setState({ backgroundColor: color });
  };
  render() {
    return (
      <div className="wrapper">
        <div className={this.state.loading ? "u-loading-layer" : ""}>
          {this.state.loading ? <Spinner color="warning" type="grow" className="c-loader" /> : ""}
          <ReduxToastr
            timeOut={4000}
            newestOnTop={true}
            preventDuplicates
            position="top-right"
            getState={(state) => state.toastr} // This is the default
            transitionIn="fadeIn"
            transitionOut="fadeOut"
            progressBar
            closeOnToastrClick
          />
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
                  <Route
                    path={prop.layout + prop.path}
                    component={prop.component}
                    key={key}
                  />
                );
              })}
            </Switch>
            <Footer fluid />
          </div>
        </div>
      </div>
    );
  }
}

const mapStateToProps = (s, p) => {
  // Dashboard loading
  const { data: account } = s.balanceInBtcReducer;
  const { data: assets } = s.assetsReducer;
  const { data: balanceDiff } = s.balanceDiffReducer;
  const dashboardData = !checkValue(account) && !checkValue(assets) && !checkValue(balanceDiff);

  // BotForm loading
  const { data: balances } = s.balanceReducer;
  const { data: symbols } = s.symbolReducer;
  const { data: bot } = s.getSingleBotReducer;
  const botFormData = !checkValue(balances) && !checkValue(symbols) && !checkValue(bot);

  if (p.location.pathname === "/admin/dashboard") {
    return {
      loading: !dashboardData
    }
  }
  return {
    loading: false
  }
};

export default connect(mapStateToProps,{})(Admin);
