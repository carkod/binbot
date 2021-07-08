import {
  Badge,
  Col,
  FormFeedback,
  Input,
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  Label,
  Row,
  TabPane,
} from "reactstrap";
import SymbolSearch from "../../../components/SymbolSearch";

export default function MainTab({
  symbols,
  state,
  handlePairChange,
  handlePairBlur,
  handleChange,
  handleBaseChange,
  handleBlur,
  addMin,
}) {
  return (
    <TabPane tabId="main">
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <SymbolSearch
            name="Pair"
            label="Select pair"
            options={symbols}
            selected={state.pair}
            handleChange={handlePairChange}
            handleBlur={handlePairBlur}
          />
        </Col>
        <Col md="6" sm="12">
          <Label htmlFor="name">Name</Label>
          <Input
            type="text"
            name="name"
            onChange={handleChange}
            value={state.name}
          />
        </Col>
      </Row>
      <Row className="u-margin-bottom">
        <Col md="6" sm="12">
          <Label htmlFor="base_order_size">
            Base order size<span className="u-required">*</span>
          </Label>
          <InputGroup>
            <Input
              type="text"
              name="base_order_size"
              onChange={handleBaseChange}
              onBlur={handleBlur}
              value={state.base_order_size}
            />
            <InputGroupAddon addonType="append">
              <InputGroupText>{state.quoteAsset}</InputGroupText>
            </InputGroupAddon>
          </InputGroup>
          <FormFeedback valid={!state.baseOrderSizeError}>
            Not enough balance
          </FormFeedback>
          <Badge color="secondary" onClick={addMin}>
            Min {state.quoteAsset === "BTC" ? 0.001 : (state.quoteAsset === "BNB" ? 0.051 : (state.quoteAsset === "GBP" ? 10 : ""))}
          </Badge>
        </Col>
      </Row>
    </TabPane>
  );
}
