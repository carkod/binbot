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
import { deleteBot, getBots, closeBot, archiveBot } from "./actions";
import ConfirmModal from "../../components/ConfirmModal";
class Bots extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      confirmModal: null,
    };
  }

  componentDidMount = () => {
    this.props.getBots();
  };

  convertPercent = (stringNum) => {
    return `${parseFloat(stringNum) * 100}%`;
  };

  handleDelete = (id) => {
    this.setState({ confirmModal: id });
  };

  confirmDelete = (option) => {
    if (parseInt(option) === 1) {
      this.props.deleteBot(this.state.confirmModal);
    } else {
      this.props.closeBot(this.state.confirmModal);
    }
    this.setState({ confirmModal: null });
  };

  getProfit = (base_price, current_price) => {
    if (!checkValue(base_price) && !checkValue(current_price)) {
      const percent =
        ((parseFloat(current_price) - parseFloat(base_price)) /
          parseFloat(base_price)) *
        100;
      return percent.toFixed(2);
    }
    return 0;
  };

  render() {
    const { bots } = this.props;
    return (
      <>
        <div className="content">
          <Row>
            {!checkValue(bots)
              ? bots.map((x, i) => (
                  <Col key={x._id.$oid} sm="6" md="4" lg="3">
                    <Card className="card-stats">
                      <CardBody>
                        <Row>
                          <Col md="8" xs="12">
                            <div className="stats">
                              <CardTitle tag="h5" className="card-title">
                                {x.pair}
                              </CardTitle>
                            </div>
                          </Col>
                          <Col md="4" xs="12">
                            <CardTitle
                              tag="h5"
                              className="card-title u-uppercase"
                            >
                              {!checkValue(x.deal) && (
                                <Badge
                                  color={
                                    this.getProfit(
                                      x.deal.buy_price,
                                      x.deal.current_price
                                    ) > 0
                                      ? "success"
                                      : "danger"
                                  }
                                >
                                  {this.getProfit(
                                    x.deal.buy_price,
                                    x.deal.current_price
                                  ) + "%"}
                                </Badge>
                              )}
                            </CardTitle>
                          </Col>
                        </Row>
                        <Row className="u-align-baseline">
                          <Col md="8" xs="12">
                            <div className="stats">
                              <p className="card-category">{x.name}</p>
                            </div>
                          </Col>
                          <Col md="4" xs="12">
                            <div className="stats">
                              <Badge
                                color={
                                  x.status === "active"
                                    ? "success"
                                    : x.status === "error"
                                    ? "warning"
                                    : x.status === "completed"
                                    ? "info"
                                    : "secondary"
                                }
                              >
                                {!checkValue(x.status) &&
                                  x.status.toUpperCase()}
                              </Badge>
                            </div>
                          </Col>
                        </Row>
                        <hr />
                        <Row>
                          <Col md="6" xs="12">
                            <div className="stats">
                              <p className="card-category">Mode</p>
                              <p className="card-category"># Safety Orders</p>
                              <p className="card-category">Bought @</p>
                              <p className="card-category">Take Profit</p>
                              {x.trailling === "true" && (
                                <p className="card-category">Trailling TP</p>
                              )}
                              <p className="card-category">Commissions</p>
                            </div>
                          </Col>
                          <Col md="6" xs="12">
                            <div className="stats">
                              <p className="card-category">
                                {!checkValue(x.mode) ? x.mode : "Unknown"}
                              </p>
                              <p className="card-category">{x.max_so_count}</p>
                              <p className="card-category">
                                {!checkValue(x.deal) && x.deal.buy_price}
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
                                {!checkValue(x.deal) && x.deal.commission}
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
                          {x.status !== "active" &&
                            <Button
                              color="secondary"
                              title="Archive bot"
                              onClick={() => {
                                this.props.archiveBot(x._id.$oid);
                              }}
                            >
                              <i className="fas fa-folder" />
                            </Button>
                          }
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
                ))
              : "No data available"}
          </Row>
        </div>
        <ConfirmModal
          close={() => this.setState({ confirmModal: null })}
          modal={this.state.confirmModal}
          handleActions={this.confirmDelete}
          acceptText={"Close orders, sell coins and delete bot"}
          cancelText={"Just delete bot"}
        >
          Closing deals will close outstanding orders, sell coins and delete bot
        </ConfirmModal>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { message } = state.botReducer;
  if (state.botReducer.data && state.botReducer.data.length > 0) {
    // Sort active status first
    const bots = state.botReducer.data.filter((a, b) => {
      if (a.status === "active") {
        return -1;
      } else {
        return 1;
      }
    });
    return {
      ...state.botReducer,
      bots: bots,
      message: message,
    };
  }

  return state;
};

export default connect(mapStateToProps, {
  getBots,
  deleteBot,
  closeBot,
  archiveBot,
})(Bots);
