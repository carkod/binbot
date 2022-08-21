import { Button, Col, Input, Label, Row, TabPane } from "reactstrap";
import BotFormTooltip from "../../../components/BotFormTooltip";
import SafetyOrderFields from "../../../components/SafetyOrderFields";

export default function SafetyOrders({
  safetyOrders,
  asset,
  quoteAsset,
  soPriceDeviation,
  handleChange,
  addSo,
  removeSo
}) {
  return (
    <TabPane tabId="safety-orders">
      <Row className="u-margin-bottom">
        <Col md="4" sm="12">
          <Label>Num of safety orders:</Label>
          <p>
            {safetyOrders &&
            Object.getPrototypeOf(safetyOrders) !== Object.prototype
              ? safetyOrders.length
              : 0}
          </p>
        </Col>
        <Col md="4" sm="12">
          <Button className="btn" color="primary" onClick={addSo}>
            <i className="fa fa-plus" />
          </Button>
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
        />
      ) : (
        ""
      )}
    </TabPane>
  );
}
