import React from "react";
import { connect } from "react-redux";
// reactstrap components
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Col,
  Nav,
  NavItem,
  NavLink,
  Row,
  TabContent,
  TabPane,
} from "reactstrap";
import { getResearchData } from "./actions";
import Signals from "./Signals";

class Research extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      activeTab: "signals",
    };
  }

  componentDidMount = () => {
    this.props.getResearchData();
  }

  toggle = (tab) => {
    const { activeTab } = this.state;
    if (activeTab !== tab) this.setState({ activeTab: tab });
  };

  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="6" sm="12">
              <Card>
                <CardHeader>
                  <CardTitle>
                    <Nav tabs>
                      <NavItem>
                        <NavLink
                          className={
                            this.state.activeTab === "signals" ? "active" : ""
                          }
                          onClick={() => this.toggle("signals")}
                        >
                          Bolliguer band signals
                        </NavLink>
                      </NavItem>
                      <NavItem>
                        <NavLink
                          className={
                            this.state.activeTab === "correlations"
                              ? "active"
                              : ""
                          }
                          onClick={() => this.toggle("correlations")}
                        >
                          Correlations
                        </NavLink>
                      </NavItem>
                    </Nav>
                  </CardTitle>
                </CardHeader>
                <CardBody>
                  {/*
                    Tab contents
                  */}
                  <TabContent activeTab={this.state.activeTab}>
                    {this.props.research &&
                      <Signals data={this.props.research} />
                    }
                    <TabPane tabId="correlations">Correlations</TabPane>
                  </TabContent>
                </CardBody>
              </Card>
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { data } = state.researchReducer;
  return {
    research: data,
  };
};

export default connect(mapStateToProps, { getResearchData })(Research);
