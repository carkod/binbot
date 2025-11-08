import React, { type FC, useContext, useEffect, useState } from "react";
import { Col, Container, Form, InputGroup, Row, Tab } from "react-bootstrap";
import { type FieldValues, useForm } from "react-hook-form";
import { useImmer } from "use-immer";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { selectBot, setField, setToggle } from "../../features/bots/botSlice";
import { BotStatus, BotStrategy, BotType, TabsKeys } from "../../utils/enums";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";
import { InputTooltip } from "./InputTooltip";
import SymbolSearch from "./SymbolSearch";
import { useParams } from "react-router";
import { SpinnerContext } from "../Layout";
import {
  useGetSymbolsQuery,
  useLazyGetOneSymbolQuery,
} from "../../features/symbolsApiSlice";
import {
  selectTestBot,
  setTestBotField,
  setTestBotToggle,
} from "../../features/bots/paperTradingSlice";

interface ErrorsState {
  pair?: string;
}

const BaseOrderTab: FC<{
  botType?: BotType;
}> = ({ botType = BotType.BOTS }) => {
  const { symbol, id } = useParams();
  const dispatch: AppDispatch = useAppDispatch();
  const { data: symbols } = useGetSymbolsQuery();
  let { bot } = useAppSelector(selectBot);
  if (botType === BotType.PAPER_TRADING) {
    const testBot = useAppSelector(selectTestBot);
    bot = testBot.paperTrading;
  }

  const { data: autotradeSettings, isLoading: loadingSettings } =
    useGetSettingsQuery();

  const [triggerGetOneSymbol] = useLazyGetOneSymbolQuery();

  const [quoteAsset, setQuoteAsset] = useState<string>("");
  const [baseAsset, setBaseAsset] = useState<string>("");
  const [errorsState, setErrorsState] = useImmer<ErrorsState>({});
  const [symbolsList, setSymbolsList] = useImmer<string[]>([]);
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
      fiat_order_size: bot.fiat_order_size,
      strategy: bot.strategy,
    },
  });
  const { spinner, setSpinner } = useContext(SpinnerContext);

  const handlePairBlur = (e) => {
    // Only when selected not typed in
    // this way we avoid any errors
    if (e.target.value) {
      if (botType === BotType.PAPER_TRADING) {
        dispatch(setTestBotField({ name: "pair", value: e.target.value }));
      } else {
        dispatch(setField({ name: "pair", value: e.target.value }));
      }
      setErrorsState((draft) => {
        delete draft["pair"];
      });
      updateQuoteBaseState(bot.pair);
    } else {
      setErrorsState((draft) => {
        draft["pair"] = "Please select a pair";
      });
    }
  };

  // Memoize composedPair to avoid unnecessary recalculation
  const updateQuoteBaseState = (pair) => {
    triggerGetOneSymbol(pair)
      .unwrap()
      .then((data) => {
        setQuoteAsset(data.quote_asset);
        setBaseAsset(data.base_asset);
      });
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

    if (symbols && symbolsList.length === 0) {
      const pairs = symbols.map((symbol) => symbol.id);
      setSymbolsList(pairs);
    }

    if (symbol && !id) {
      reset({
        name: bot.name,
        fiat_order_size: bot.fiat_order_size,
        strategy: bot.strategy,
        pair: symbol,
        quote_asset: bot.quote_asset,
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
      });
    }

    if (bot.pair && !(Boolean(quoteAsset) || Boolean(baseAsset))) {
      updateQuoteBaseState(bot.pair);
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
    symbols,
    symbolsList,
    bot,
    reset,
    dispatch,
    watch,
    bot.pair,
    bot.quote_asset,
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
          {bot.pair && (
            <Row>
              <Col md="6" sm="12" className="my-6">
                <InputTooltip
                  name="base_order_size"
                  tooltip={"Amount of base asset to trade"}
                  label="Base order size"
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
              </Col>
            </Row>
          )}
        </Row>
      </Container>
    </Tab.Pane>
  );
};

export default BaseOrderTab;
