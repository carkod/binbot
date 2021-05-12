import React from "react";
import { connect } from "react-redux";
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  Col,
  Badge,
  Row,
} from "reactstrap";
import { checkValue } from "../../validations";
import { deleteBot, getBots } from "./actions";

class Bots extends React.Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  componentDidMount = () => {
    this.props.getBots();
  };

  convertPercent = (stringNum) => {
    return `${parseFloat(stringNum) * 100}%`;
  };

  handleDelete = (id) => {
    this.props.deleteBot(id);
  };

  getProfit = (base_price, current_price) => {
    if (!checkValue(base_price) && !checkValue(current_price)) {
      const bp = parseFloat(base_price);
      const cp = parseFloat(current_price);
      const percent = (cp - bp) / base_price;
      return percent.toFixed(2);
    }
    return 0
  }

  render() {
    const { bots } = this.props;
    return (
      <>
        <div className="content">
          <Row>
            {!checkValue(bots) ?
              bots.map((x, i) => (
                <Col key={x._id.$oid} lg="4">
                  <Card className="card-stats">
                    <CardBody>
                      <Row>
                        <Col md="7" xs="12">
                          <div className="stats">
                            <CardTitle tag="h5" className="card-title">
                              {x.pair}
                            </CardTitle>
                          </div>
                        </Col>
                        <Col md="5" xs="12">
                          <CardTitle
                            tag="h5"
                            className="card-title u-uppercase"
                          >
                            {!checkValue(x.deal) &&
                            <Badge color={this.getProfit(x.deal.buy_price, x.deal.current_price) > 0 ? "success" : "danger"} >
                              {this.getProfit(x.deal.buy_price, x.deal.current_price) + "%"}
                            </Badge>
                            }
                          </CardTitle>
                        </Col>
                      </Row>
                      <Row className="u-align-baseline">
                        <Col md="7" xs="12">
                          <div className="stats">
                            <p className="card-category">{x.name}</p>
                          </div>
                        </Col>
                        <Col md="5" xs="12">
                          <div className="stats">
                            <Badge
                              color={
                                x.active === "true" ? "success" : "secondary"
                              }
                            >
                              {x.active === "true" ? "ACTIVE" : "INACTIVE"}
                            </Badge>
                          </div>
                        </Col>
                      </Row>
                      <hr />
                      <Row>
                        <Col md="7" xs="12">
                          <div className="stats">
                            <p className="card-category">Balance Use</p>
                            <p className="card-category"># Safety Orders</p>
                            <p className="card-category">Bought @</p>
                            <p className="card-category">Take Profit</p>
                            {x.trailling === "true" && (
                              <p className="card-category">Trailling TP</p>
                            )}
                            <p className="card-category">Total commissions</p>
                          </div>
                        </Col>
                        <Col md="4" xs="12">
                          <div className="stats">
                            <p className="card-category">
                              {parseFloat(x.balance_usage) * 100 + "%"}
                            </p>
                            <p className="card-category">{x.max_so_count}</p>
                            <p className="card-category">
                            {!checkValue(x.deal) &&
                              x.deal.buy_price
                            }
                            </p>
                            <p className="card-category">
                              {x.take_profit + "%"}
                            </p>
                            {x.trailling === "true" && (
                              <p className="card-category">
                                {x.trailling_deviation + "%"}
                              </p>
                            )}
                            <p className="card-category">
                              {!checkValue(x.deal) &&
                                x.deal.commission
                              }
                            </p>
                          </div>
                        </Col>
                      </Row>
                    </CardBody>
                    <CardFooter>
                      <hr />
                      <div className="u-space-between">
                        <Button
                          color="info"
                          onClick={() =>
                            this.props.history.push(
                              `/admin/bots-edit/${x._id.$oid}`
                            )
                          }
                        >
                          <i className="fas fa-edit" />
                        </Button>
                        <Button
                          color="danger"
                          onClick={() => this.handleDelete(x._id.$oid)}
                        >
                          <i className="fas fa-trash" />
                        </Button>
                      </div>
                    </CardFooter>
                  </Card>
                </Col>
              )) : "No data available"}
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { message } = state.botReducer;
  if (state.botReducer.data && state.botReducer.data.length > 0) {
    // Sort active status first
    const bots = state.botReducer.data.filter((a, b) => {
      if (a.active === "true") {
        return -1;
      } else {
        return 1;
      }
    });
    const inactiveBots = state.botReducer.data.filter((a, b) => {
      if (a.active === "false") {
        return -1;
      } else {
        return 1;
      }
    });
    return {
      ...state.botReducer,
      bots: bots,
      inactive: inactiveBots,
      message: message,
    };
  }

  return state;
};

export default connect(mapStateToProps, {
  getBots,
  deleteBot,
})(Bots);
