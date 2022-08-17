import {
  Col,
  Input,
  InputGroup,
  InputGroupText,
  Label,
  Row,
  TabPane,
} from "reactstrap";
import BotFormTooltip from "../../../components/BotFormTooltip";

const renderSafetyOrders = (
  so_list,
  asset,
  quoteAsset,
  handleChange,
  handleBlur
) => {
  return (
    <>
      {so_list.map((e, i) => (
        <Row key={i} className="u-margin-bottom">
          <Col md="4" sm="12">
            <Label htmlFor={e.name}>Name</Label>
            <Input
              type="text"
              name={e.name}
              onChange={handleChange}
              onBlur={handleBlur}
            />
          </Col>
          <Col md="4" sm="12">
            <Label htmlFor="buy_price">Buy price</Label>
            <InputGroup>
              <Input
                type="text"
                name={e.buy_price}
                onChange={handleChange}
                onBlur={handleBlur}
              />
              <InputGroupText>{quoteAsset}</InputGroupText>
            </InputGroup>
          </Col>
          <Col md="4" sm="12">
            <Label htmlFor="so_size">Buy quantity</Label>
            <InputGroup>
              <Input
                type="text"
                name={e.so_size}
                onChange={handleChange}
                onBlur={handleBlur}
              />
              <InputGroupText>{asset.replace(quoteAsset, "")}</InputGroupText>
            </InputGroup>
          </Col>
        </Row>
      ))}
    </>
  );
};

export default function SafetyOrders({
  numSafetyOrders,
  safetyOrders,
  asset,
  quoteAsset,
  soPriceDeviation,
  handleChange,
  handleBlur,
}) {
  return (
    <TabPane tabId="safety-orders">
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label for="numSafetyOrders">Num of safety orders:</Label>
          <Input
            type="number"
            name="numSafetyOrders"
            id="numSafetyOrders"
            onChange={handleChange}
            onBlur={handleBlur}
            value={numSafetyOrders}
          />
        </Col>
        <Col md="6" sm="12">
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
            onBlur={handleBlur}
            value={soPriceDeviation}
          />
        </Col>
      </Row>
      {safetyOrders && Object.getPrototypeOf(safetyOrders) !== Object.prototype
        ? renderSafetyOrders(safetyOrders, asset, quoteAsset, handleChange, handleBlur)
        : ""}
    </TabPane>
  );
}
