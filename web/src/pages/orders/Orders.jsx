import CardTable from "components/CardTable";
import React from "react";
import { connect } from "react-redux";
import { Col, Row } from "reactstrap";
import { getOrders, getOpenOrders, pollOrders } from "./actions";

class Orders extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      limit: 10,
      offset: 0
    }
  }

  componentDidMount = () => {
    const { limit, offset } = this.state;
    this.props.getOrders(limit, offset);
    // this.props.getOpenOrders();
  }

  handleLoadPage = (limit, offset) => {
    this.setState({ offset: offset });
    this.props.getOrders(limit, offset);
  }


  render() {
    return (
      <>
        <div className="content">
          <Row>
            <Col md="12">
              <CardTable 
                title={"Historical orders"}
                data={this.props.orders}
                pages={this.props.pages}
                limit={this.state.limit}
                loadPage={this.handleLoadPage}
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
  return {
    orders: orders,
    pages: pages
  };

}

export default connect(mapStateToProps, { getOrders, getOpenOrders, pollOrders })(Orders);
