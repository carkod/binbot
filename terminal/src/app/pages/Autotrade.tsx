import {
  Box,
  Button,
  Card,
  Group,
  Input,
  NativeSelect,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Title,
} from "@mantine/core";
import { useEffect, type FC } from "react";
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
import { BinanceKlineintervals, ExchangeId } from "../../utils/enums";
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
    register,
    watch,
    setValue,
    reset,
    handleSubmit,
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
      trailing: settings.trailing,
      trailing_deviation: settings.trailing_deviation,
      trailing_profit: settings.trailing_profit,
      telegram_signals: settings.telegram_signals,
      autoswitch: settings.autoswitch,
      exchange_id: settings.exchange_id,
      grid_allocation_pct: settings.grid_allocation_pct,
      grid_cash_reserve_pct: settings.grid_cash_reserve_pct,
      grid_total_margin: settings.grid_total_margin,
      grid_level_count: settings.grid_level_count,
      grid_max_active_ladders: settings.grid_max_active_ladders,
      max_margin_per_ladder_pct: settings.max_margin_per_ladder_pct,
      enable_grid_ladders: settings.enable_grid_ladders,
    },
  });

  const handleBlur = (e) => {
    const { name, value } = e.target;

    if (name && value) {
      if (typeof value === "string") {
        dispatch(setSettingsField({ name, value }));
      } else {
        dispatch(setSettingsToggle({ name, value }));
      }
    }
  };

  const saveSettings = async (formData) => {
    await updateSettings({ ...settings, ...formData }).unwrap();
  };

  useEffect(() => {
    if (data) {
      dispatch(setSettings(data));
    }
  }, [data]);
  useEffect(() => {
    const { unsubscribe } = watch((v, { name, type }) => {
      if (v && v?.[name]) {
        if (typeof v[name] === "boolean") {
          dispatch(setSettingsToggle({ name, value: v[name] }));
        } else {
          dispatch(
            setSettingsField({ name, value: v[name] as number | string }),
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
        trailing: settings.trailing,
        trailing_deviation: settings.trailing_deviation,
        trailing_profit: settings.trailing_profit,
        telegram_signals: settings.telegram_signals,
        autoswitch: settings.autoswitch,
        exchange_id: settings.exchange_id,
        grid_allocation_pct: settings.grid_allocation_pct,
        grid_cash_reserve_pct: settings.grid_cash_reserve_pct,
        grid_total_margin: settings.grid_total_margin,
        grid_level_count: settings.grid_level_count,
        grid_max_active_ladders: settings.grid_max_active_ladders,
        max_margin_per_ladder_pct: settings.max_margin_per_ladder_pct,
        enable_grid_ladders: settings.enable_grid_ladders,
      });
    }
    return () => unsubscribe();
  }, [dispatch, settings]);
  return (
    <Box w="100%">
      <form onSubmit={handleSubmit(saveSettings)}>
        <Card mb="md" mt={16}>
          <Box mb="sm">
            <Box>
              <Title order={4}>General bot autotrade</Title>
              <Text fz=".875rem" fw={300} lh={1}>
                These settings trigger Bots automatically given the parameters.
                They use the same services and endpoints as Bots.
              </Text>
              <Text fz=".875rem" fw={300} lh={1}>
                Bots that are autotrade will be set with mode: autotrade
              </Text>
            </Box>
          </Box>
          <Box>
            <Box w="100%">
              <Box>
                <SimpleGrid cols={{ base: 1, md: 4 }}>
                  <Stack gap={4} mb="sm">
                    <Input.Label htmlFor="exchange_id">
                      Select Exchange
                    </Input.Label>
                    <NativeSelect
                      id="exchange_id"
                      name="exchange_id"
                      onChange={(e) => {
                        const { value } = e.target;

                        dispatch(
                          setSettingsField({
                            name: "exchange_id",
                            value,
                          }),
                        );
                      }}
                      onBlur={handleBlur}
                      {...register("exchange_id", {
                        required: true,
                      })}
                    >
                      {Object.values(ExchangeId).map((exchange, i) => (
                        <option key={i} value={exchange.toString()}>
                          {exchange.toString()}
                        </option>
                      ))}
                    </NativeSelect>
                    {errors.exchange_id && (
                      <Input.Error>
                        {errors.exchange_id.message as string}
                      </Input.Error>
                    )}
                    <Input.Description>
                      <strong>Attention:</strong> Critical setting. If this is
                      changed bots, balances, symbols/charts will be set to use
                      this exchange&apos;s data
                    </Input.Description>
                  </Stack>

                  <Box>
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
                  </Box>
                  <Box></Box>
                </SimpleGrid>
                <SimpleGrid cols={{ base: 1, md: 4 }}>
                  <Box>
                    <label htmlFor="autotrade">Autotrade?</label>
                    <br />
                    <Group gap="xs">
                      <Switch
                        id="autotrade"
                        checked={settings.autotrade}
                        onChange={(e) => {
                          dispatch(
                            setSettingsToggle({
                              name: "autotrade",
                              value: !settings.autotrade,
                            }),
                          );
                        }}
                        label={settings.autotrade ? "On" : "Off"}
                      />
                    </Group>
                  </Box>
                  <NativeSelect
                    id="candlestick_interval"
                    name="candlestick_interval"
                    onChange={(e) => {
                      const { value } = e.target;

                      dispatch(
                        setSettingsField({
                          name: "candlestick_interval",
                          value,
                        }),
                      );
                    }}
                    onBlur={handleBlur}
                    {...register("candlestick_interval", {
                      required: true,
                    })}
                  >
                    {Object.values(BinanceKlineintervals).map((interval, i) => (
                      <option key={i} value={interval.toString()}>
                        {interval.toString()}
                      </option>
                    ))}
                  </NativeSelect>
                  <SettingsInput
                    value={settings.max_active_autotrade_bots}
                    name={"max_active_autotrade_bots"}
                    label={"Max active autotrade bots"}
                    handleBlur={handleBlur}
                    register={register}
                  />
                </SimpleGrid>
                <SimpleGrid cols={{ base: 1, md: 4 }}>
                  <SettingsInput
                    value={settings.base_order_size}
                    name={"base_order_size"}
                    label={"Base order size (quantity)"}
                    type="text"
                    register={register}
                  />
                  <SettingsInput
                    value={settings.fiat}
                    name={"fiat"}
                    label={"Fiat currency to use for trading"}
                    type="text"
                    register={register}
                    infoText="Careful! This is a global change of everything, from candlesticks to charts and bots as well as Binquant analytics"
                  />
                </SimpleGrid>
                <hr />
                <SimpleGrid cols={{ base: 1, md: 4 }}>
                  <SettingsInput
                    value={settings.stop_loss}
                    name={"stop_loss"}
                    label={"Stop loss"}
                    type="number"
                    register={register}
                  />
                  <Box>
                    <label htmlFor="autoswitch">Autoswitch?</label>
                    <br />
                    <Group gap="xs">
                      <Switch
                        id="autoswitch"
                        checked={settings.autoswitch}
                        onChange={(e) => {
                          dispatch(
                            setSettingsToggle({
                              name: "autoswitch",
                              value: !settings.autoswitch,
                            }),
                          );
                        }}
                        label={settings.autoswitch ? "On" : "Off"}
                      />
                    </Group>
                  </Box>
                </SimpleGrid>
                <hr />
                <SimpleGrid cols={{ base: 1, md: 4 }}>
                  <Box>
                    <label htmlFor="trailing">Trailing</label>
                    <br />
                    <LightSwitch
                      value={settings.trailing}
                      name="trailing"
                      register={register}
                      toggle={(name, value) => {
                        setValue("trailing", !value);
                        dispatch(
                          setSettingsToggle({
                            name: name,
                            value: !value,
                          }),
                        );
                      }}
                    />
                  </Box>
                </SimpleGrid>
                {settings.trailing ? (
                  <SimpleGrid cols={{ base: 1, md: 4 }}>
                    <SettingsInput
                      value={settings.trailing_deviation}
                      name={"trailing_deviation"}
                      label={"Trailing stop loss"}
                      type="number"
                      infoText="Should be kept as small as possible as this will increase funds needed to start base_order_size"
                      register={register}
                    />
                    <SettingsInput
                      value={settings.trailing_profit}
                      name={"trailing_profit"}
                      label={"Trail profit"}
                      type="number"
                      register={register}
                    />
                  </SimpleGrid>
                ) : (
                  <SimpleGrid cols={{ base: 1, md: 4 }}>
                    <SettingsInput
                      value={settings.take_profit}
                      name={"take_profit"}
                      label={"Take profit"}
                      type="number"
                      register={register}
                    />
                  </SimpleGrid>
                )}
              </Box>
            </Box>
          </Box>
        </Card>
        <Card mb="md" mt={16}>
          <Box mb="sm">
            <Box>
              <Title order={4}>Grid trading</Title>
              <Text fz=".875rem" fw={300} lh={1}>
                Allocation and ladder limits for automatic futures grid
                deployments.
              </Text>
            </Box>
          </Box>
          <Box>
            <Box w="100%">
              <SimpleGrid cols={{ base: 1, md: 4 }}>
                <Box>
                  <label htmlFor="enable_grid_ladders">
                    Enable grid ladders?
                  </label>
                  <br />
                  <Group gap="xs">
                    <Switch
                      id="enable_grid_ladders"
                      checked={settings.enable_grid_ladders}
                      onChange={(e) => {
                        dispatch(
                          setSettingsToggle({
                            name: "enable_grid_ladders",
                            value: !settings.enable_grid_ladders,
                          }),
                        );
                      }}
                      label={settings.enable_grid_ladders ? "On" : "Off"}
                    />
                  </Group>
                </Box>
              </SimpleGrid>
              {settings.enable_grid_ladders && (
                <>
                  <hr />
                  <SimpleGrid cols={{ base: 1, md: 4 }}>
                    <SettingsInput
                      value={settings.grid_allocation_pct}
                      name={"grid_allocation_pct"}
                      label={"Grid allocation pct"}
                      type="number"
                      register={register}
                    />
                    <SettingsInput
                      value={settings.grid_cash_reserve_pct}
                      name={"grid_cash_reserve_pct"}
                      label={"Grid cash reserve pct"}
                      type="number"
                      register={register}
                    />
                    <SettingsInput
                      value={settings.grid_total_margin}
                      name={"grid_total_margin"}
                      label={"Grid total margin"}
                      type="number"
                      register={register}
                    />
                  </SimpleGrid>
                  <SimpleGrid cols={{ base: 1, md: 4 }}>
                    <SettingsInput
                      value={settings.grid_level_count}
                      name={"grid_level_count"}
                      label={"Grid level count"}
                      type="number"
                      step={1}
                      register={register}
                    />
                    <SettingsInput
                      value={settings.grid_max_active_ladders}
                      name={"grid_max_active_ladders"}
                      label={"Grid max active ladders"}
                      type="number"
                      step={1}
                      register={register}
                    />
                    <SettingsInput
                      value={settings.max_margin_per_ladder_pct}
                      name={"max_margin_per_ladder_pct"}
                      label={"Max margin per ladder pct"}
                      type="number"
                      register={register}
                    />
                  </SimpleGrid>
                </>
              )}
            </Box>
          </Box>
        </Card>
        <SimpleGrid cols={1} mt={16} mb={16}>
          <Box>
            <Button color="primary" type="submit">
              Save
            </Button>{" "}
          </Box>
        </SimpleGrid>
      </form>
    </Box>
  );
};

export default AutotradePage;
