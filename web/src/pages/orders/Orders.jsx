import CardTable from "components/CardTable";
import Tables from "components/Tables";
import React from "react";
import { connect } from "react-redux";
import { Col, Row } from "reactstrap";
import { dataHeaders } from "../../validations";
import { deleteOpenOrders, getOpenOrders, getOrders, pollOrders } from "./actions";

class Orders extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      limit: 10,
      offset: 0,
      status: "FILLED"
    }
  }

  componentDidMount = () => {
    this.props.getOrders(this.state);
    this.props.getOpenOrders();
  }

  handleLoadPage = (limit, offset, status) => {
    if (status === "" || status === undefined) status = null;
    this.setState({ offset: offset, limit: limit, status: status }, () => 
      this.props.getOrders(this.state)
    );
  }

  updateHistoricalOrders = (e) => {
    e.preventDefault();
    this.props.pollOrders();
  }

  handleDeleteOrder = (element) => {
    this.props.deleteOpenOrders(element);
  }

  handleFilter = (e) => {
    let stateName = e.target.name;
    if (stateName === "") stateName = null;
    this.setState({ [stateName]: e.target.value }, () => {
      this.props.getOrders(this.state);
    });
  }


  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              {this.props.openOrders && <Tables 
                title={"Opened orders"}
                headers={dataHeaders}
                data={this.props.openOrders}
                action={this.handleDeleteOrder}
                />}
            </Col>
          </Row>
          <Row>
            <Col md="12">
              <CardTable 
                title={"Historical orders"}
                data={this.props.orders}
                pages={this.props.pages}
                limit={this.state.limit}
                loadPage={this.handleLoadPage}
                updateData={this.updateHistoricalOrders}
                filter={this.handleFilter}
                />
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { pages, data: orders } = state.ordersReducer;
  const { data: openOrders } = state.openOrdersReducer;
  return {
    orders: orders,
    pages: pages,
    openOrders: openOrders
  };

}

export default connect(mapStateToProps, { getOrders, getOpenOrders, pollOrders, deleteOpenOrders })(Orders);
