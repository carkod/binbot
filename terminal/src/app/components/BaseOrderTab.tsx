import { type FC, useEffect, useState } from "react";
import {
  Badge,
  Col,
  Container,
  Form,
  InputGroup,
  Row,
  Tab,
} from "react-bootstrap";
import { type FieldValues, useForm } from "react-hook-form";
import { useImmer } from "use-immer";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { selectBot, setField, setToggle } from "../../features/bots/botSlice";
import { useGetSymbolsQuery } from "../../features/symbolApiSlice";
import { getQuoteAsset } from "../../utils/api";
import { BotStatus, BotStrategy, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";
import { InputTooltip } from "./InputTooltip";
import SymbolSearch from "./SymbolSearch";
import { useParams } from "react-router";

interface ErrorsState {
  pair?: string;
}

const BaseOrderTab: FC = () => {
  const { symbol } = useParams();
  const dispatch: AppDispatch = useAppDispatch();
  const { data } = useGetSymbolsQuery();
  const { bot } = useAppSelector(selectBot);
  const { data: autotradeSettings } = useGetSettingsQuery();
  const [quoteAsset, setQuoteAsset] = useState<string>("");
  const [errorsState, setErrorsState] = useImmer<ErrorsState>({});
  const [symbolsList, setSymbolsList] = useState<string[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const {
    register,
    watch,
    reset,
    formState: { errors },
  } = useForm<FieldValues>({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      name: bot.name,
      base_order_size: bot.base_order_size,
      cooldown: bot.cooldown,
      strategy: bot.strategy,
    },
  });

  const addMin = () => {
    dispatch(setField({ name: "base_order_size", value: 0.001 }));
  };

  const addAll = () => {
    // fix: replace value with the full balance
    // dispatch(setField({ name: "base_order_size", value: 0.001 }));
  };

  const handlePairBlur = (e) => {
    // Only when selected not typed in
    // this way we avoid any errors
    if (e.target.value) {
      dispatch(setField({ name: "pair", value: e.target.value }));
      setErrorsState((draft) => {
        delete draft["pair"];
      });
    } else {
      setErrorsState((draft) => {
        draft["pair"] = "Please select a pair";
      });
    }
  };

  // Data
  useEffect(() => {
    const { unsubscribe } = watch((v, { name, type }) => {
      if (v && v?.[name]) {
        if (typeof v === "boolean") {
          dispatch(setToggle({ name, value: v[name] }));
        } else {
          dispatch(setField({ name, value: v[name] as number | string }));
        }
      }
    });

    if (data) {
      setSymbolsList(data);
    }

    if (bot.pair) {
      setQuoteAsset(getQuoteAsset(bot, autotradeSettings?.balance_to_use));
    }

    if (bot.pair && bot.base_order_size) {
      reset({
        name: bot.name,
        base_order_size: bot.base_order_size,
        cooldown: bot.cooldown,
        strategy: bot.strategy,
      });
    }

    if (symbol) {
      dispatch(setField({ name: "pair", value: symbol }));
    }

    if (bot.deal?.current_price) {
      setCurrentPrice(bot.deal.current_price);
    }

    return () => unsubscribe();
  }, [
    data,
    symbolsList,
    setSymbolsList,
    bot,
    quoteAsset,
    setQuoteAsset,
    reset,
    autotradeSettings?.balance_to_use,
    dispatch,
    symbol,
    watch,
  ]);

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
              value={bot.pair}
              onBlur={handlePairBlur}
              required
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
                secondaryText={autotradeSettings?.balance_to_use}
              >
                <Form.Control
                  type="number"
                  name="base_order_size"
                  autoComplete="off"
                  required
                  disabled={
                    bot.status === BotStatus.ACTIVE ||
                    bot.status === BotStatus.COMPLETED
                  }
                  {...register("base_order_size", {
                    required: "Base order size is required",
                    valueAsNumber: true,
                    min: {
                      value: 15,
                      message: "Minimum base order size is 15",
                    },
                  })}
                />
                {errors.base_order_size && (
                  <Form.Control.Feedback type="invalid">
                    {errors.base_order_size.message as string}
                  </Form.Control.Feedback>
                )}
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
            <InputTooltip
              name="base_order_size"
              tooltip={"Amount of asset to trade"}
              label="Asset amount"
              errors={errors}
              secondaryText={quoteAsset}
            >
              <Form.Control
                type="number"
                name="base_order_size"
                autoComplete="off"
                disabled={true}
                value={bot.base_order_size * currentPrice}
              />
            </InputTooltip>
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
                {...register("cooldown")}
              />
            </InputTooltip>
          </Col>
        </Row>
        <Row>
          <Col md="6" sm="12">
            <Form.Group>
              <Form.Label htmlFor="strategy">Strategy</Form.Label>
              <Form.Select
                id="strategy"
                name="strategy"
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
  );
};

export default BaseOrderTab;
