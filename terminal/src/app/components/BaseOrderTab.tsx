import { type FC, useEffect, useState } from "react"
import {
  Badge,
  Col,
  Container,
  Form,
  InputGroup,
  Row,
  Tab,
} from "react-bootstrap"
import { type FieldValues, useForm } from "react-hook-form"
import { selectBot, setField } from "../../features/bots/botSlice"
import { useGetSymbolsQuery } from "../../features/symbolApiSlice"
import { BotStatus, BotStrategy, TabsKeys } from "../../utils/enums"
import { useAppDispatch, useAppSelector } from "../hooks"
import { type AppDispatch } from "../store"
import { InputTooltip } from "./InputTooltip"
import SymbolSearch from "./SymbolSearch"
import { useImmer } from "use-immer"

interface ErrorsState {
  pair?: string
}

const BaseOrderTab: FC = () => {
  const dispatch: AppDispatch = useAppDispatch()
  const { data } = useGetSymbolsQuery()
  const { bot } = useAppSelector(selectBot)
  const [pair, setPair] = useState<string>(bot.pair)
  const [quoteAsset, setQuoteAsset] = useState<string>("")
  const [errorsState, setErrorsState] = useImmer<ErrorsState>({})
  const [symbolsList, setSymbolsList] = useState<string[]>([])
  const {
    register,
    handleSubmit,
    getValues,
    reset,
    control,
    formState: { errors },
  } = useForm<FieldValues>()

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const value = getValues(e.target.name)
    if (value) {
      dispatch(setField({ name: e.target.name, value: value }))
    }
  }

  const addMin = () => {
    dispatch(setField({ name: "base_order_size", value: 0.001 }))
  }

  const addAll = () => {
    dispatch(setField({ name: "base_order_size", value: 0.001 }))
  }

  const handlePairChange = (selected: string[]) => {
    if (selected?.length === 0) {
      setErrorsState(draft => {
        delete draft["pair"]
      })
    } else {
      setPair(selected[0])
    }
  }

  const handlePairBlur = e => {
    // Only when selected not typed in
    // this way we avoid any errors
    if (pair) {
      dispatch(setField({ name: "pair", value: pair }))
    } else {
      setErrorsState(draft => {
        draft["pair"] = "Please select a pair"
      })
    }
  }

  useEffect(() => {
    if (data) {
      setSymbolsList(data)
    }
    if (bot.pair) {
      setPair(bot.pair)
      setQuoteAsset(bot.pair.replace(bot.balance_to_use, ""))
    }
    if (bot) {
      for (const key in bot) {
        reset({ [key]: bot[key] })
      }
    }
  }, [
    data,
    symbolsList,
    setSymbolsList,
    pair,
    setPair,
    bot,
    quoteAsset,
    setQuoteAsset,
    reset,
  ])

  return (
    <Tab.Pane id="base-order-tab" eventKey={TabsKeys.MAIN} className="mb-3">
      <Container>
        <Row className="my-3">
          <Col md="6" sm="12">
            <SymbolSearch
              name="pair"
              label="Select pair"
              options={symbolsList}
              disabled={bot.status === BotStatus.COMPLETED}
              onChange={handlePairChange}
              onBlur={handlePairBlur}
              value={pair}
              required={true}
              errors={errorsState}
            />
          </Col>
          <Col md="6" sm="12">
            <Form.Label htmlFor="name">Name</Form.Label>
            <Form.Control type="text" name="name" {...register("name")} />
          </Col>
        </Row>
        <Row className="my-3">
          <Col md="6" sm="12">
            <InputGroup className="mb-1">
              <InputTooltip
                name="base_order_size"
                tooltip={"Minimum 15 USD"}
                label="Base order size"
                errors={errors}
                required={true}
                secondaryText={quoteAsset}
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
            </InputGroup>
            {bot.status !== BotStatus.ACTIVE && (
              <>
                <Badge color="secondary" onClick={addMin}>
                  Min{" "}
                  {quoteAsset === "BTC"
                    ? 0.001
                    : quoteAsset === "BNB"
                      ? 0.051
                      : quoteAsset === "USDC"
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
                  {errors.strategy.message as string}
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
