import React, { useEffect, type FC } from "react";
import { Button, Card, Col, Container, Form, Row } from "react-bootstrap";
import { useForm, type FieldValues } from "react-hook-form";
import LightSwitch from "../components/LightSwitch";
import SettingsInput from "../components/SettingsInput";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";
import { BinanceKlineintervals } from "../../utils/enums";
import { useEditTestSettingsMutation, useGetTestSettingsQuery } from "../../features/testAutotradeApiSlice";
import { selectTestSettings, setTestSettings, setTestSettingsField, setTestSettingsToggle } from "../../features/testAutotradeSlice";
import type { FocusEvent as ReactFocusEvent } from "react";

export const TestAutotradePage: FC<{}> = () => {
  const { data } = useGetTestSettingsQuery();
  const dispatch: AppDispatch = useAppDispatch();
  const { settings } = useAppSelector(selectTestSettings);
  const [updateSettings] = useEditTestSettingsMutation();

  const {
    register,
    setValue,
    reset,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FieldValues>({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      candlestick_interval: settings.candlestick_interval,
      autotrade: settings.autotrade,
      max_active_autotrade_bots: settings.max_active_autotrade_bots,
      base_order_size: settings.base_order_size,
      fiat: settings.fiat,
      stop_loss: settings.stop_loss,
      take_profit: settings.take_profit,
      trailling: settings.trailling,
      trailling_deviation: settings.trailling_deviation,
      trailling_profit: settings.trailling_profit,
      autoswitch: settings.autoswitch,
    },
  });

  const handleBlur = (e: FocusEvent | ReactFocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (e.target && 'name' in e.target && 'value' in e.target && e.target.name && e.target.value) {
      const name = e.target.name;
      const value = e.target.value;
      if (typeof value === "string") {
        dispatch(setTestSettingsField({ name, value }));
      } else {
        dispatch(setTestSettingsToggle({ name, value }));
      }
    }
  };

  const saveSettings = async (formData) => {
    await updateSettings(formData).unwrap();
  };

  useEffect(() => {

    if (data) {
      dispatch(setTestSettings(data));
    }
  }, [data]);

useEffect(() => {
    const { unsubscribe } = watch((v, { name, type }) => {
      if (v && v?.[name]) {
        if (typeof v[name] === "boolean") {
          dispatch(setTestSettingsToggle({ name, value: v[name] }));
        } else {
          dispatch(
            setTestSettingsField({ name, value: v[name] as number | string })
          );
        }
      }
    });

    if (settings) {
      reset({
        candlestick_interval: settings.candlestick_interval,
        autotrade: settings.autotrade,
        max_active_autotrade_bots: settings.max_active_autotrade_bots,
        base_order_size: settings.base_order_size,
        fiat: settings.fiat,
        stop_loss: settings.stop_loss,
        take_profit: settings.take_profit,
        trailling: settings.trailling,
        trailling_deviation: settings.trailling_deviation,
        trailling_profit: settings.trailling_profit,
        autoswitch: settings.autoswitch,
      });
    }

    return () => unsubscribe();
  }, [dispatch, settings]);

  return (
    <Container>
      <Card className="mt-3">
        <Card.Header>
          <Row>
            <Col md="12">
              <Card.Title>Bot Autotrade settings for test</Card.Title>
              <p className="fs-6 fw-light lh-1">
                These settings trigger Paper trading bots automatically given the parameters.
                They use the same services and endpoints as Paper Trading.
                Since bots don&apos;t trigger in exchange, base order size will not be used
              </p>
              <p className="fs-6 fw-light lh-1">
                Bots that are autotrade will be set with mode: <strong>autotrade</strong>
              </p>
            </Col>
          </Row>
        </Card.Header>
        <Card.Body>
          <Container>
            <Row>
              <Col md={"12"} sm="12">
                <Row>
                  <Col md="3">
                    <Form.Group>
                      <Form.Label htmlFor="candlestick_interval">
                        {"Candlestick interval"}
                      </Form.Label>
                      <Form.Select
                        id="candlestick_interval"
                        name="candlestick_interval"
                        onChange={(e) => {
                          const { value } = e.target;
                          dispatch(
                            setTestSettingsField({
                              name: "candlestick_interval",
                              value,
                            })
                          );
                        }}
                        onBlur={handleBlur}
                        defaultValue={settings.candlestick_interval}
                        {...register("candlestick_interval", {
                          required: true,
                        })}
                      >
                        {Object.values(BinanceKlineintervals).map(
                          (interval, i) => (
                            <option key={i} value={interval.toString()}>
                              {interval.toString()}
                            </option>
                          )
                        )}
                      </Form.Select>
                      {errors.candlestick_interval && (
                        <Form.Control.Feedback>
                          {errors.candlestick_interval.message as string}
                        </Form.Control.Feedback>
                      )}
                      <Form.Control.Feedback tooltip>
                        Autotrade uses this interval to get candlestick data for
                        technical analysis and decides to trade using this
                        horizon.
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>

                  <Col md="3">
                    <label htmlFor="telegram_signals">
                      Send messages to telegram?
                    </label>
                    <br />
                    <LightSwitch
                      value={settings.telegram_signals}
                      name="telegram_signals"
                      register={register}
                      toggle={(name, value) => {
                        setValue(name, !value);
                        dispatch(
                          setTestSettingsToggle({
                            name: name,
                            value: !value,
                          })
                        );
                      }}
                    />
                  </Col>
                  <Col md="3"></Col>
                </Row>
                <Row>
                  <Col md="3">
                    <label htmlFor="autotrade">Autotrade?</label>
                    <br />
                    <LightSwitch
                      value={settings.autotrade}
                      name="autotrade"
                      register={register}
                      toggle={(name, value) => {
                        setValue(name, !value);
                        dispatch(
                          setTestSettingsToggle({
                            name: name,
                            value: !value,
                          })
                        );
                      }}
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={settings.max_active_autotrade_bots}
                      name={"max_active_autotrade_bots"}
                      label={"Max active autotrade bots"}
                      handleBlur={handleBlur}
                      register={register}
                    />
                  </Col>
                </Row>
                <Row>
                  <Col md="3">
                    <SettingsInput
                      value={settings.base_order_size}
                      name={"base_order_size"}
                      label={"Base order size (quantity)"}
                      type="text"
                      register={register}
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={settings.fiat}
                      name={"fiat"}
                      label={"Fiat currency to use for trading"}
                      type="text"
                      register={register}
                      infoText="Careful! This is a global change of everything, from candlesticks to charts and bots as well as Binquant analytics"
                    />
                  </Col>
                </Row>
                <hr />
                <Row>
                  <Col md="3">
                    <SettingsInput
                      value={settings.stop_loss}
                      name={"stop_loss"}
                      label={"Stop loss"}
                      type="number"
                      register={register}
                    />
                  </Col>
                  <Col md="3">
                    <label htmlFor="autoswitch">Autoswitch?</label>
                    <br />
                    <LightSwitch
                      value={settings.autoswitch}
                      name="autoswitch"
                      register={register}
                      toggle={(name, value) => {
                        setValue(name, !value);
                        dispatch(
                          setTestSettingsToggle({
                            name: name,
                            value: !value,
                          })
                        );
                      }}
                    />
                  </Col>
                </Row>
                <hr />
                <Row>
                  <Col md="3">
                    <label htmlFor="trailling">Trailling</label>
                    <br />
                    <LightSwitch
                      value={settings.trailling}
                      name="trailling"
                      register={register}
                      toggle={(name, value) => {
                        setValue("trailling", !value);
                        dispatch(
                          setTestSettingsToggle({
                            name: name,
                            value: !value,
                          })
                        );
                      }}
                    />
                  </Col>
                </Row>
                {settings.trailling ? (
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={settings.trailling_deviation}
                        name={"trailling_deviation"}
                        label={"Trailling stop loss"}
                        type="number"
                        infoText="Should be kept as small as possible as this will increase funds needed to start base_order_size"
                        register={register}
                      />
                    </Col>
                    <Col md="3">
                      <SettingsInput
                        value={settings.trailling_profit}
                        name={"trailling_profit"}
                        label={"Trail profit"}
                        type="number"
                        register={register}
                      />
                    </Col>
                  </Row>
                ) : (
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={settings.take_profit}
                        name={"take_profit"}
                        label={"Take profit"}
                        type="number"
                        register={register}
                      />
                    </Col>
                  </Row>
                )}
                <br />
                <Row>
                  <Col>
                    <Button
                      color="primary"
                      onClick={handleSubmit(saveSettings)}
                    >
                      Save
                    </Button>{" "}
                  </Col>
                </Row>
                <br />
              </Col>
            </Row>
          </Container>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default TestAutotradePage;
