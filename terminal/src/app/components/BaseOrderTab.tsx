import { type FC, useEffect, useState } from "react"
import { Badge, Col, Container, Form, InputGroup, Row, Stack, Tab } from "react-bootstrap"
import { useForm } from "react-hook-form"
import { useAppDispatch } from "../hooks"
import { type Bot, singleBot } from "../../features/bots/botInitialState"
import { type AppDispatch } from "../store"
import { InputTooltip } from "./InputTooltip"
import { setField } from "../../features/bots/botSlice"
import { TabsKeys } from "../pages/BotDetail"
import { BotStatus, BotStrategy } from "../../utils/enums"

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
      <Container>
        <Row className="my-3">
          <Col md="6" sm="12">
            {/* <SymbolSearch
            name="Pair"
            label="Select pair"
            options={symbols}
            selected={bot.pair}
            handleChange={handlePairChange}
            handleBlur={handlePairBlur}
            disabled={bot.status === BotStatus.COMPLETED}
            required={true}
          /> */}
          </Col>
          <Col md="6" sm="12">
            <Form.Label htmlFor="name">Name</Form.Label>
            <Form.Control
              type="text"
              name="name"
              value={bot.name}
              {...register("name")}
            />
          </Col>
        </Row>
        <Row className="my-3">
          <Col md="6" sm="12">
            <InputGroup>
              <InputTooltip
                name="base_order_size"
                tooltip={"Minimum 15 USD"}
                title="Base order size"
                label="Base order size"
                errors={errors}
              >
                <Form.Control
                  type="text"
                  name="base_order_size"
                  onBlur={handleBlur}
                  value={bot.base_order_size}
                  autoComplete="off"
                  required
                  disabled={
                    bot.status === BotStatus.ACTIVE ||
                    bot.status === BotStatus.COMPLETED
                  }
                  {...register("base_order_size", {
                    required: "Base order size is required",
                    min: {
                      value: 15,
                      message: "Minimum base order size is 15",
                    },
                  })}
                />
              </InputTooltip>
              {bot.quoteAsset && (
                <InputGroup.Text>{bot.quoteAsset}</InputGroup.Text>
              )}
            </InputGroup>

            {bot.status !== BotStatus.ACTIVE && (
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
          <Col md="6" sm="12">
            <Stack direction="horizontal">
              <Badge>{bot.balance_to_use}</Badge>
            </Stack>
          </Col>
        </Row>
        <Row className="my-3">
          <Col md="6" sm="12">
            <InputTooltip
              name="cooldown"
              tooltip="Time until next bot activation with same pair"
              label="Cooldown (seconds)"
              title="Cooldown"
              errors={errors}
              {...register("cooldown")}
            >
              <Form.Control
                type="number"
                name="cooldown"
                value={bot.cooldown}
                autoComplete="off"
              />
            </InputTooltip>
          </Col>
        </Row>
        <Row>
          <Col md="6" sm="12">
            <Form.Group>
              <Form.Label htmlFor="strategy">Trigger strategy</Form.Label>
              <Form.Select
                id="strategy"
                name="strategy"
                value={bot.strategy}
                onBlur={handleBlur}
                {...register("strategy", { required: "Strategy is required" })}
              >
                <option value={BotStrategy.LONG}>Long</option>
                <option value={BotStrategy.MARGIN_SHORT}>Margin short</option>
              </Form.Select>
              {errors.strategy && (
                <Form.Control.Feedback type="invalid">
                  {errors.strategy.message}
                </Form.Control.Feedback>
              )}
            </Form.Group>
          </Col>
        </Row>
      </Container>
    </Tab.Pane>
  )
}

export default BaseOrderTab
