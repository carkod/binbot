import React, { type FC, useContext, useEffect, useState } from "react";
import {
  Col,
  Container,
  Form,
  FormLabel,
  InputGroup,
  Row,
  Tab,
} from "react-bootstrap";
import { type FieldValues, useForm } from "react-hook-form";
import { useImmer } from "use-immer";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { selectBot, setField, setToggle } from "../../features/bots/botSlice";
import {
  BotStatus,
  BotStrategy,
  BotType,
  MarketType,
  TabsKeys,
} from "../../utils/enums";
import { useAppDispatch, useAppSelector, useSymbolData } from "../hooks";
import { type AppDispatch } from "../store";
import { InputTooltip } from "./InputTooltip";
import SymbolSearch from "./SymbolSearch";
import { useParams } from "react-router";
import { SpinnerContext } from "../Layout";
import {
  selectTestBot,
  setTestBotField,
  setTestBotToggle,
} from "../../features/bots/paperTradingSlice";
import InputGroupText from "react-bootstrap/esm/InputGroupText";

interface ErrorsState {
  pair?: string;
}

const BaseOrderTab: FC<{
  botType?: BotType;
}> = ({ botType = BotType.BOTS }) => {
  const { symbol, id } = useParams();
  const dispatch: AppDispatch = useAppDispatch();
  const { symbolsList, quoteAsset, baseAsset, updateQuoteBaseState } =
    useSymbolData();
  let { bot } = useAppSelector(selectBot);
  if (botType === BotType.PAPER_TRADING) {
    const testBot = useAppSelector(selectTestBot);
    bot = testBot.paperTrading;
  }

  const { data: autotradeSettings, isLoading: loadingSettings } =
    useGetSettingsQuery();

  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [errorsState, setErrorsState] = useImmer<ErrorsState>({});
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
      fiat_order_size: bot.fiat_order_size,
      strategy: bot.strategy,
    },
  });
  const { spinner, setSpinner } = useContext(SpinnerContext);

  const handlePairBlur = (e) => {
    // Only when selected not typed in
    // this way we avoid any errors
    if (e.target.value) {
      const pair = e.target.value;
      if (botType === BotType.PAPER_TRADING) {
        dispatch(setTestBotField({ name: "pair", value: pair }));
      } else {
        dispatch(setField({ name: "pair", value: pair }));
      }
      setErrorsState((draft) => {
        delete draft["pair"];
      });
      updateQuoteBaseState(pair);
    } else {
      setErrorsState((draft) => {
        draft["pair"] = "Please select a pair";
      });
    }
  };

  // Data
  useEffect(() => {
    const { unsubscribe } = watch((v, { name }) => {
      if (v && v?.[name]) {
        if (typeof v === "boolean") {
          if (botType === BotType.PAPER_TRADING) {
            dispatch(setTestBotToggle({ name, value: v[name] }));
          } else {
            dispatch(setToggle({ name, value: v[name] }));
          }
        } else {
          if (botType === BotType.PAPER_TRADING) {
            dispatch(setTestBotField({ name, value: v[name] }));
          } else {
            dispatch(setField({ name, value: v[name] }));
          }
        }
      }
    });

    if (symbol && !id) {
      reset({
        name: bot.name,
        fiat_order_size: bot.fiat_order_size,
        strategy: bot.strategy,
        pair: symbol,
        quote_asset: bot.quote_asset,
        market_type: bot.market_type,
      });
      if (botType === BotType.PAPER_TRADING) {
        dispatch(setTestBotField({ name: "pair", value: symbol }));
      } else {
        dispatch(setField({ name: "pair", value: symbol }));
      }
    }

    if (id && !symbol) {
      reset({
        name: bot.name,
        fiat_order_size: bot.fiat_order_size,
        strategy: bot.strategy,
        pair: id,
        quote_asset: bot.quote_asset,
        market_type: bot.market_type,
      });
    }

    if (
      bot.deal?.current_price !== currentPrice &&
      bot.deal?.closing_price === 0
    ) {
      setCurrentPrice(bot.deal.current_price);
    }

    if (!loadingSettings && autotradeSettings) {
      setSpinner(false);
    }

    return () => unsubscribe();
  }, [
    quoteAsset,
    baseAsset,
    reset,
    dispatch,
    watch,
    bot.pair,
    bot.quote_asset,
    bot.market_type,
  ]);

  return (
    <Tab.Pane id="base-order-tab" eventKey={TabsKeys.MAIN} className="mb-3">
      <Container>
        <Row className="my-3">
          <Col md="6" sm="12">
            <SymbolSearch
              name="pair"
              label="Select pair"
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
                name="fiat_order_size"
                tooltip={
                  "This is the amount of fiat (Minimum USDC 15) you want to spend, while asset amount (quote asset) indicates the intermediary crypto used to buy, because it may not available in USDC"
                }
                label="Fiat order size"
                errors={errors}
                required={true}
                secondaryText={autotradeSettings?.fiat}
              >
                <Form.Control
                  type="number"
                  name="fiat_order_size"
                  autoComplete="off"
                  required
                  disabled={
                    bot.status === BotStatus.ACTIVE ||
                    bot.status === BotStatus.COMPLETED
                  }
                  {...register("fiat_order_size", {
                    required: "Fiat order size is required",
                    valueAsNumber: true,
                    min: {
                      value: 15,
                      message: "Minimum fiat order size is 15",
                    },
                  })}
                />
                {errors.fiat_order_size && (
                  <Form.Control.Feedback type="invalid">
                    {errors.fiat_order_size.message as string}
                  </Form.Control.Feedback>
                )}
              </InputTooltip>
            </InputGroup>
          </Col>
          <Col md="6" sm="12">
            <Row>
              <Col>
                <Form.Group>
                  <Form.Label htmlFor="strategy">Strategy</Form.Label>
                  <Form.Select
                    id="strategy"
                    name="strategy"
                    {...register("strategy", {
                      required: "Strategy is required",
                    })}
                  >
                    <option value={BotStrategy.LONG}>Long</option>
                    <option value={BotStrategy.MARGIN_SHORT}>
                      Margin short
                    </option>
                  </Form.Select>
                  {errors.strategy && (
                    <Form.Control.Feedback type="invalid">
                      {errors.strategy.message as string}
                    </Form.Control.Feedback>
                  )}
                </Form.Group>
              </Col>
            </Row>
          </Col>
          {bot.pair && (
            <Row>
              <Col md="6" sm="12" className="my-6">
                <InputTooltip
                  name="base_order_size"
                  tooltip={"Notional size (position size * leverage)"}
                  label={
                    bot.market_type === MarketType.FUTURES
                      ? "Contract size"
                      : "Base order size"
                  }
                  errors={errors}
                  secondaryText={quoteAsset}
                >
                  <Form.Control
                    type="number"
                    name="base_order_size"
                    autoComplete="off"
                    disabled={true}
                    value={bot.deal.base_order_size}
                  />
                </InputTooltip>
              </Col>
              <Col md="6" sm="12" className="my-6">
                {bot.market_type === MarketType.FUTURES ? (
                  <div>
                    <FormLabel>Leverage:</FormLabel>
                    <InputGroupText>3x (harcoded)</InputGroupText>
                  </div>
                ) : (
                  <>
                    <InputTooltip
                      name="total_asset_amount"
                      tooltip={"Amount of asset to trade"}
                      label="Asset amount"
                      errors={errors}
                      secondaryText={baseAsset}
                    >
                      <Form.Control
                        type="number"
                        name="total_asset_amount"
                        autoComplete="off"
                        disabled={true}
                        value={bot.deal.base_order_size * currentPrice}
                      />
                    </InputTooltip>
                  </>
                )}
              </Col>
            </Row>
          )}
        </Row>
      </Container>
    </Tab.Pane>
  );
};

export default BaseOrderTab;
