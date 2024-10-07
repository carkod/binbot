import { type FC, useEffect, useState } from "react"
import { Badge, Col, Form, Row, Tab } from "react-bootstrap"
import { useForm } from "react-hook-form"
import { useAppDispatch } from "../hooks"
import { type Bot, singleBot } from "../../features/bots/botInitialState"
import { type AppDispatch } from "../store"
import { InputTooltip } from "./InputTooltip"
import { setField } from "../../features/bots/botSlice"
import { TabsKeys } from "../pages/BotDetail"

const BaseOrderTab: FC<{
  bot: Bot
}> = ({ bot }) => {
  const dispatch: AppDispatch = useAppDispatch()
  const [activeTab, setActiveTab] = useState<TabsKeys>(TabsKeys.MAIN)

  const handleTabClick = (tab: TabsKeys) => {
    setActiveTab(tab)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    dispatch(setField({ name, value }))
  }

  const handleBaseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    dispatch(setField({ name, value }))
  }

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    dispatch(setField({ name, value }))
  }

  const addMin = () => {
    dispatch(setField({ name: "base_order_size", value: 0.001 }))
  }

  const addAll = () => {
    dispatch(setField({ name: "base_order_size", value: 0.001 }))
  }

  const {
    register,
    watch,
    formState: { errors },
  } = useForm<Bot>({
    mode: "onTouched",
    reValidateMode: "onSubmit",
    defaultValues: singleBot,
  })

  useEffect(() => {
    const subscription = watch((value, { name, type }) => {
      console.log(">>", value, name, type)
    })

    return () => subscription.unsubscribe()
  }, [watch])

  return (
    <Tab.Pane id="main" eventKey={TabsKeys.MAIN} className="mb-3">
      <Row>
        <Col md="6" sm="12">
          {/* <SymbolSearch
            name="Pair"
            label="Select pair"
            options={symbols}
            selected={bot.pair}
            handleChange={handlePairChange}
            handleBlur={handlePairBlur}
            disabled={bot.status === "completed"}
            required={true}
          /> */}
        </Col>
        <Col md="6" sm="12">
          <Form.Label htmlFor="name">Name</Form.Label>
          <Form.Control
            type="text"
            name="name"
            onChange={handleChange}
            value={bot.name}
            {...register("name")}
          />
        </Col>
      </Row>
      {/* <Row>
        <Col md="6" sm="12">
          <InputTooltip name="base_order_size" tooltip={"Minimum 15 USD"} title="Base order size">
            <Form.Control
              type="text"
              name="base_order_size"
              onChange={handleBaseChange}
              onBlur={handleBlur}
              value={bot.base_order_size}
              autoComplete="off"
              required
              disabled={bot.status === "active" || bot.status === "completed"}
            />
          </InputTooltip>
          
          {bot.status !== "active" && (
            <>
              <Badge color="secondary" onClick={addMin}>
                Min{" "}
                {bot.quoteAsset === "BTC"
                  ? 0.001
                  : bot.quoteAsset === "BNB"
                    ? 0.051
                    : bot.quoteAsset === "USDC"
                      ? 15
                      : ""}
              </Badge>{" "}
              <Badge color="secondary" onClick={addAll}>
                Add all
              </Badge>
            </>
          )}
        </Col>
        {bot.status !== "active" && (
          <Col md="6" sm="12">
            <Form.Label htmlFor="balance_to_use" aria-required="true">
              Balance to use
            </Form.Label>
            <Form.Group
              style={{
                display: "flex",
                alignItems: "center",
                fontSize: "1.5rem",
              }}
            >
              {bot.quoteAsset && (
                <Form.Label>
                  <Form.Control
                    required
                    type="radio"
                    name="balance_to_use"
                    checked={bot.balance_to_use === bot.quoteAsset}
                    value={bot.quoteAsset}
                    onChange={handleChange}
                  />{" "}
                  {bot.quoteAsset}
                </Form.Label>
              )}
              <Form.Label>
                <Form.Control
                  type="radio"
                  name="balance_to_use"
                  checked={bot.balance_to_use === "GBP"}
                  value={"GBP"}
                  onChange={handleChange}
                />{" "}
                GBP
              </Form.Label>
            </Form.Group>
          </Col>
        )}
      </Row> */}
      {/* <Row>
        <Col md="6" sm="12">
          <Form.Group>
            <InputTooltip
              name="cooldown"
              text="Time until next bot activation with same pair"
            >
              Cooldown (seconds)
            </InputTooltip>
            <Form.Control
              type="number"
              name="cooldown"
              onChange={handleChange}
              value={bot.cooldown}
              autoComplete="off"
            />
          </Form.Group>
        </Col>
      </Row> */}
      {/* <Row>
        <Col md="6" sm="12">
          <Form.Group>
            <Form.Label htmlFor="strategy">Trigger strategy</Form.Label>
            <Form.Control
              id="strategy"
              name="strategy"
              type="select"
              value={bot.strategy}
              onChange={handleChange}
              onBlur={handleBlur}
            >
              <option value="long">Long</option>
              <option value="margin_short">Margin short</option>
            </Form.Control>
          </Form.Group>
        </Col>
      </Row> */}
    </Tab.Pane>
  )
}

export default BaseOrderTab
