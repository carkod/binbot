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
import BotFormTooltip from "../../../components/BotFormTooltip";
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
            disabled={state.status === "completed"}
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
            <BotFormTooltip
              name="base_order_size"
              text="Not important, real funds not used"
            >
              Base order size
            </BotFormTooltip>
            <span className="u-required">*</span>
          </Label>
          <InputGroup>
            <Input
              type="text"
              name="base_order_size"
              onChange={handleBaseChange}
              onBlur={handleBlur}
              value={state.base_order_size}
              autoComplete="off"
              disabled={
                state.status === "active" || state.status === "completed"
              }
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
      <Row>
        <Col md="6">
          <FormGroup>
            <BotFormTooltip
              name="short_sell_price"
              text="Price at which to stop loss sell and later buy again with short_buy_price (short strategy autoswitch)"
            >
              Short Sell Price
            </BotFormTooltip>
            <InputGroup>
              <Input
                type="number"
                name="short_sell_price"
                onBlur={handleBlur}
                onChange={handleChange}
                value={state.short_sell_price}
                autoComplete="off"
                step="0.00000001"
              />
              <InputGroupText>{state.quoteAsset}</InputGroupText>
            </InputGroup>
          </FormGroup>
        </Col>
        <Col md="6" sm="12">
          <FormGroup>
            <BotFormTooltip
              name="cooldown"
              text="Time until next bot activation with same pair"
            >
              Cooldown (seconds)
            </BotFormTooltip>
            <Input
              type="number"
              name="cooldown"
              onChange={handleChange}
              value={state.cooldown}
              autoComplete="off"
            />
          </FormGroup>
        </Col>
      </Row>
      <Row>
        <Col md="6" sm="12">
          <FormGroup>
            <Label for="strategy">Trigger strategy</Label>
            <Input
              id="strategy"
              name="strategy"
              type="select"
              value={state.strategy}
              onChange={handleChange}
              onBlur={handleBlur}
            >
              <option value="long">Long</option>
              <option value="short">Short</option>
            </Input>
          </FormGroup>
        </Col>
        <Col md="6" sm="12">
          <FormGroup>
            <BotFormTooltip
              name="short_buy_price"
              text="Price at which to execute base order"
            >
              Short Buy Price
            </BotFormTooltip>
            <InputGroup>
              <Input
                type="number"
                name="short_buy_price"
                onChange={handleChange}
                onBlur={handleBlur}
                value={state.short_buy_price}
                autoComplete="off"
                step="0.00000001"
              />
              <InputGroupText>{state.quoteAsset}</InputGroupText>
            </InputGroup>
          </FormGroup>
        </Col>
      </Row>
    </TabPane>
  );
}
