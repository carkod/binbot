import { Button, Col, Input, Label, Row, TabPane } from "reactstrap";
import BotFormTooltip from "./BotFormTooltip";
import SafetyOrderFields from "./SafetyOrderFields";

export default function SafetyOrdersTab({
  safetyOrders,
  asset,
  quoteAsset,
  soPriceDeviation,
  handleChange,
  addSo,
  removeSo,
  handleBlur,
}) {

  const activeSo = Object.getPrototypeOf(safetyOrders) === Object.prototype ? [] : safetyOrders.map(x => x.status === 0)

  return (
    <TabPane tabId="safety-orders">
      <Row className="u-margin-bottom">
        <Col md="4" sm="12">
          <Label>Total safety orders:</Label>
          <p>
            {safetyOrders &&
            Object.getPrototypeOf(safetyOrders) !== Object.prototype
              ? safetyOrders.length
              : 0}
          </p>
        </Col>
        <Col md="3" sm="12">
          <Button className="btn" color="primary" onClick={addSo}>
            <i className="fa fa-plus" />
          </Button>
        </Col>
        <Col md="3" sm="12">
          <Label>Active safety orders:</Label>
          <p>
            {activeSo &&
            Object.getPrototypeOf(activeSo) !== Object.prototype
              ? activeSo.length
              : 0}
          </p>
        </Col>
        <Col md="4" sm="12">
          <BotFormTooltip
            name="so_price_deviation"
            text="% distance between each safety order"
          >
            Price deviation (%):
          </BotFormTooltip>
          <Input
            type="number"
            name="so_price_deviation"
            id="so_price_deviation"
            onChange={handleChange}
            value={soPriceDeviation}
          />
        </Col>
      </Row>
      {safetyOrders &&
      Object.getPrototypeOf(safetyOrders) !== Object.prototype ? (
        <SafetyOrderFields
          safetyOrders={safetyOrders}
          asset={asset}
          quoteAsset={quoteAsset}
          handleChange={handleChange}
          removeSo={removeSo}
          handleBlur={handleBlur}
        />
      ) : (
        ""
      )}
    </TabPane>
  );
}
