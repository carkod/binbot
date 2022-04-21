import {
  Badge,
  Col,
  FormFeedback,
  FormGroup,
  Input,
  InputGroup,
  InputGroupText,
  Label,
  Row,
  TabPane,
} from "reactstrap";
import SymbolSearch from "../../../components/SymbolSearch";
import { checkValue } from "../../../validations";

export default function MainTab({
  symbols,
  state,
  handlePairChange,
  handlePairBlur,
  handleChange,
  handleBaseChange,
  handleBlur,
  addMin,
  addAll,
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
              autoComplete="off"
              disabled={state.status === "active"}
            />
            <InputGroupText>{state.quoteAsset}</InputGroupText>
          </InputGroup>
          <FormFeedback valid={!state.baseOrderSizeError}>
            Not enough balance
          </FormFeedback>
          {state.status !== "active" && (
            <>
              <Badge color="secondary" onClick={addMin}>
                Min{" "}
                {state.quoteAsset === "BTC"
                  ? 0.001
                  : state.quoteAsset === "BNB"
                  ? 0.051
                  : state.quoteAsset === "GBP"
                  ? 10
                  : ""}
              </Badge>{" "}
              <Badge color="secondary" onClick={addAll}>
                Add all
              </Badge>
            </>
          )}
          <FormFeedback valid={!checkValue(state.addAllError)}>
            state.addAllError
          </FormFeedback>
        </Col>
        {state.status !== "active" && (
          <Col md="6" sm="12">
            <Label htmlFor="balance_to_use">
              Balance to use<span className="u-required">*</span>
            </Label>
            <FormGroup
              check
              style={{
                display: "flex",
                alignItems: "center",
                fontSize: "1.5rem",
              }}
            >
              {state.quoteAsset && (
                <Label check>
                  <Input
                    type="radio"
                    name="balance_to_use"
                    checked={state.balance_to_use === state.quoteAsset}
                    value={state.quoteAsset}
                    onChange={handleChange}
                  />{" "}
                  {state.quoteAsset}
                </Label>
              )}
              <Label check>
                <Input
                  type="radio"
                  name="balance_to_use"
                  checked={state.balance_to_use === "GBP"}
                  value={"GBP"}
                  onChange={handleChange}
                />{" "}
                GBP
              </Label>
            </FormGroup>
          </Col>
        )}
      </Row>
    </TabPane>
  );
}
