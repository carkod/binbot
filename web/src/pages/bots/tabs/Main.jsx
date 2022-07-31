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
  bot,
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
            selected={bot.pair}
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
            value={bot.name}
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
              value={bot.base_order_size}
              autoComplete="off"
              disabled={bot.status === "active"}
            />
            <InputGroupText>{bot.quoteAsset}</InputGroupText>
          </InputGroup>
          <FormFeedback valid={!bot.baseOrderSizeError}>
            Not enough balance
          </FormFeedback>
          {bot.status !== "active" && (
            <>
              <Badge color="secondary" onClick={addMin}>
                Min{" "}
                {bot.quoteAsset === "BTC"
                  ? 0.001
                  : bot.quoteAsset === "BNB"
                  ? 0.051
                  : bot.quoteAsset === "GBP"
                  ? 10
                  : ""}
              </Badge>{" "}
              <Badge color="secondary" onClick={addAll}>
                Add all
              </Badge>
            </>
          )}
          <FormFeedback valid={!checkValue(bot.addAllError)}>
            bot.addAllError
          </FormFeedback>
        </Col>
        {bot.status !== "active" && (
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
              {bot.quoteAsset && (
                <Label check>
                  <Input
                    type="radio"
                    name="balance_to_use"
                    checked={bot.balance_to_use === bot.quoteAsset}
                    value={bot.quoteAsset}
                    onChange={handleChange}
                  />{" "}
                  {bot.quoteAsset}
                </Label>
              )}
              <Label check>
                <Input
                  type="radio"
                  name="balance_to_use"
                  checked={bot.balance_to_use === "GBP"}
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
              value={bot.cooldown}
              autoComplete="off"
            />
          </FormGroup>
        </Col>
      </Row>
    </TabPane>
  );
}
