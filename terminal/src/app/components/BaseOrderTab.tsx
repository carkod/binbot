import { type FC, SetStateAction, useEffect, useState } from "react"
import {
  Badge,
  Col,
  Container,
  Form,
  InputGroup,
  Row,
  Tab,
} from "react-bootstrap"
import {
  FieldArrayMethodProps,
  type FieldValues,
  FormProps,
  useController,
  useForm,
  useFormContext,
  UseFormProps,
  type UseFormRegister,
  UseFormStateProps,
} from "react-hook-form"
import { useAppDispatch, useAppSelector } from "../hooks"
import { type Bot, singleBot } from "../../features/bots/botInitialState"
import { type AppDispatch } from "../store"
import { InputTooltip } from "./InputTooltip"
import { setField } from "../../features/bots/botSlice"
import { TabsKeys } from "../pages/BotDetail"
import { BotStatus, BotStrategy } from "../../utils/enums"
import SymbolSearch from "./SymbolSearch"
import { useGetSymbolsQuery } from "../../features/symbolApiSlice"
import { BotFormController } from "./BotDetailTabs"

const BaseOrderTab: FC<{
  bot: Bot
}> = ({ bot }) => {
  const dispatch: AppDispatch = useAppDispatch()
  const { data } = useGetSymbolsQuery()
  const [pair, setPair] = useState<string>(bot.pair)
  const [symbolsList, setSymbolsList] = useState<string[]>([])

  const { control, register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: singleBot,
  })

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

  const handlePairChange = (selected: string[]) => {
    setPair(selected[0])
  }

  const handlePairBlur = e => {
    dispatch(setField({ name: "pair", value: e.target.value }))
  }

  useEffect(() => {
    if (data) {
      setSymbolsList(data)
    }
  }, [data, symbolsList, setSymbolsList])

  return (
    <Tab.Pane id="base-order-tab" eventKey={TabsKeys.MAIN} className="mb-3">
      <Container>
        <Row className="my-3">
          <Col md="6" sm="12">
            <SymbolSearch
              name="Pair"
              label="Select pair"
              options={symbolsList}
              disabled={bot.status === BotStatus.COMPLETED}
              required={true}
              onBlur={handlePairBlur}
              selected={symbolsList.filter((symbol) => symbol === pair)}
            />
          </Col>
          <Col md="6" sm="12">
            <Form.Label htmlFor="name">Name</Form.Label>
            <Form.Control type="text" name="name" defaultValue={bot.name} />
          </Col>
        </Row>
        <Row className="my-3">
          <Col md="6" sm="12">
            <InputGroup>
              <InputTooltip
                name="base_order_size"
                tooltip={"Minimum 15 USD"}
                label="Base order size"
                // errors={errors}
                required={true}
              >
                <Form.Control
                  type="text"
                  name="base_order_size"
                  onBlur={handleBlur}
                  defaultValue={bot.base_order_size}
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
          <Col md="6" sm="12" className="my-6">
            <Form.Label htmlFor="balance_to_use">Balance to use</Form.Label>
            <br />
            <Form.Text>
              <Badge bg="secondary" className="fs-6">
                {bot.balance_to_use}
              </Badge>
            </Form.Text>
          </Col>
        </Row>
        <Row className="my-3">
          <Col md="6" sm="12">
            <InputTooltip
              name="cooldown"
              tooltip="Time until next bot activation with same pair"
              label="Cooldown (seconds)"
              errors={errors}
            >
              <Form.Control
                type="number"
                name="cooldown"
                onBlur={handleBlur}
                defaultValue={bot.cooldown}
                {...register("cooldown")}
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
                defaultValue={bot.strategy}
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
