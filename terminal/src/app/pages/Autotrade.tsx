import { useEffect, type FC } from "react";
import { Button, Card, Col, Container, Row } from "react-bootstrap";
import { useForm, type FieldValues } from "react-hook-form";
import {
  useEditSettingsMutation,
  useGetSettingsQuery,
} from "../../features/autotradeApiSlice";
import {
  selectSettings,
  setSettings,
  setSettingsField,
  setSettingsToggle,
} from "../../features/autotradeSlice";
import LightSwitch from "../components/LightSwitch";
import SettingsInput from "../components/SettingsInput";
import { useAppDispatch, useAppSelector } from "../hooks";
import { type AppDispatch } from "../store";

export const AutotradePage: FC<{}> = () => {
  const { data } = useGetSettingsQuery();
  const dispatch: AppDispatch = useAppDispatch();
  const { settings } = useAppSelector(selectSettings);
  const [updateSettings] = useEditSettingsMutation();

  const {
    control,
    watch,
    register,
    setValue,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm<FieldValues>({
    mode: "onTouched",
    reValidateMode: "onBlur",
    defaultValues: {
      candlestick_interval: settings.candlestick_interval,
    },
  });

  const handleBlur = (e) => {
    if (e.target.name && e.target.value) {
      const name = e.target.name;
      const value = e.target.value;
      if (typeof value === "string") {
        dispatch(setSettingsField({ name, value }));
      } else {
        dispatch(setSettingsToggle({ name, value }));
      }
    }
  };

  const saveSettings = async (data) => {
    await updateSettings(data).unwrap();
  };

  useEffect(() => {
    if (data) {
      reset(data);
    }
  }, [data, dispatch, reset, setValue]);

  return (
    <Container>
      <Card className="mt-3">
        <Card.Header>
          <Row>
            <Col md="12">
              <Card.Title>General bot autotrade</Card.Title>
              <p className="fs-6 fw-light lh-1">
                These settings trigger Bots automatically given the parameters.
                They use the same services and endpoints as Bots.
              </p>
              <p className="fs-6 fw-light lh-1">
                Bots that are autotrade will be set with mode: autotrade
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
                    <SettingsInput
                      name={"candlestick_interval"}
                      label={"Candlestick interval"}
                      handleBlur={handleBlur}
                      register={register}
                      value={settings.candlestick_interval}
                    />
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
                          setSettingsToggle({
                            name: name,
                            value: !value,
                          }),
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
                        setValue(name, value);
                        dispatch(
                          setSettingsToggle({
                            name: name,
                            value: !value,
                          }),
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
                      value={settings.balance_to_use}
                      name={"balance_to_use"}
                      label={"Balance to use"}
                      type="text"
                      register={register}
                      infoText="Careful! This is a global change of everything, from candlesticks to charts and bots as well as Binquant analytics"
                    />
                  </Col>
                  <Col md="3">
                    <SettingsInput
                      value={settings.trailling_deviation}
                      name={"trailling_deviation"}
                      label={"Trailling deviation"}
                      type="number"
                      register={register}
                    />
                  </Col>
                </Row>
                <Row>
                  <Col md="3">
                    <label htmlFor="trailling">Trailling</label>
                    <br />
                    <Button
                      name="trailling"
                      color={settings.trailling ? "success" : "secondary"}
                      onClick={() => {
                        setValue("trailling", !settings.trailling);
                        dispatch(
                          setSettingsToggle({
                            name: "trailling",
                            value: !settings.trailling,
                          }),
                        );
                      }}
                      {...register("trailling", { required: true })}
                    >
                      {settings.trailling ? "On" : "Off"}
                    </Button>
                  </Col>
                </Row>
                {settings.trailling && (
                  <Row>
                    <Col md="3">
                      <SettingsInput
                        value={settings.stop_loss}
                        name={"stop_loss"}
                        label={"Stop loss"}
                        type="number"
                        infoText="Should be kept as small as possible as this will increase funds needed to start base_order_size"
                        register={register}
                      />
                    </Col>
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

export default AutotradePage;
