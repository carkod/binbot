import {
  Box,
  Button,
  Card,
  Grid,
  Input,
  Stack,
  TextInput,
  Title,
  VisuallyHidden,
} from "@mantine/core";
import { type FC, useEffect, useState } from "react";
import { type FieldValues, useForm } from "react-hook-form";
import {
  type SymbolRequestPayload,
  useDeleteSymbolMutation,
  useGetSymbolsQuery,
  useUpdateSymbolMutation,
} from "../../features/symbolsApiSlice";
import ConfirmModal from "../components/ConfirmModal";
import LightSwitch from "../components/LightSwitch";
import SymbolSearch from "../components/SymbolSearch";
const SymbolsPage: FC = () => {
  const { data: symbols } = useGetSymbolsQuery();
  const [updateSymbol] = useUpdateSymbolMutation();
  const [deleteSymbol] = useDeleteSymbolMutation();
  const [symbolsList, setSymbolsList] = useState<string[]>([]);
  const [seletedSymbolsItem, setSeletedSymbolsItem] =
    useState<SymbolRequestPayload>({
      id: "",
      blacklist_reason: "",
      active: true,
      cooldown: 0,
      cooldown_start_ts: 0,
      futures_leverage: 1,
      exchange_id: "",
      base_asset: "",
      quote_asset: "",
    });
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);
  const {
    register,
    setValue,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm<FieldValues>({
    mode: "onTouched",
    reValidateMode: "onBlur",
  });
  useEffect(() => {
    if (symbols && symbols.length > 0) {
      const pairs = symbols.map((symbol) => symbol.id);
      setSymbolsList(pairs);
    }
  }, [symbols]);
  const selectSymbol = (pair: string) => {
    const symbol = symbols.find((s) => s.id === pair);
    if (symbol) {
      setSeletedSymbolsItem({
        id: symbol.id,
        blacklist_reason: symbol.blacklist_reason,
        active: symbol.active,
        cooldown: symbol.cooldown,
        cooldown_start_ts: symbol.cooldown_start_ts,
        futures_leverage: symbol.futures_leverage,
        exchange_id: symbol.exchange_id,
        base_asset: symbol.base_asset,
        quote_asset: symbol.quote_asset,
      });
    }
  };
  return (
    <div className="content">
      <Card mb="md">
        <Box mb="sm">
          <Title order={4}>Symbols</Title>
        </Box>
        <Box>
          {symbols && symbols.length > 0 && (
            <Grid>
              <Grid.Col
                span={{
                  base: 12,
                  md: 6,
                }}
              >
                <SymbolSearch
                  name="pair"
                  label="Select pair"
                  options={symbolsList}
                  required
                  errors={errors}
                  onChange={selectSymbol}
                  onBlur={(event) => selectSymbol(event.target.value)}
                />
              </Grid.Col>
              {symbolsList && seletedSymbolsItem.id !== "" && (
                <Grid.Col
                  span={{
                    base: 12,
                    md: 6,
                  }}
                >
                  <Grid>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 4,
                      }}
                    >
                      <Stack gap={4} mb="sm">
                        <label htmlFor="telegram_signals">Active?</label>
                        <br />
                        <LightSwitch
                          value={seletedSymbolsItem.active}
                          name="active"
                          register={register}
                          toggle={(name, value) => {
                            setSeletedSymbolsItem({
                              ...seletedSymbolsItem,
                              active: !value,
                            });
                          }}
                        />
                      </Stack>
                    </Grid.Col>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 8,
                      }}
                    >
                      <Stack gap={4} mb="sm">
                        <label htmlFor="blacklist_reason">
                          Blacklisted reason
                        </label>
                        <TextInput
                          type="text"
                          name="blacklist_reason"
                          id="blacklist_reason"
                          defaultValue={seletedSymbolsItem.blacklist_reason}
                          onBlur={(e) =>
                            setSeletedSymbolsItem({
                              ...seletedSymbolsItem,
                              blacklist_reason: e.target.value,
                            })
                          }
                        />
                      </Stack>
                    </Grid.Col>
                  </Grid>
                  <br />
                  <Grid>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 6,
                      }}
                    >
                      <Stack gap={4} mb="sm">
                        <Input.Label htmlFor="cooldown">Cooldown</Input.Label>
                        <TextInput
                          type="number"
                          name="cooldown"
                          id="cooldown"
                          value={seletedSymbolsItem.cooldown}
                          onChange={(e) => {
                            setSeletedSymbolsItem({
                              ...seletedSymbolsItem,
                              cooldown: parseInt(e.target.value),
                              cooldown_start_ts:
                                parseInt(e.target.value) > 0 &&
                                new Date().getTime(),
                            });
                          }}
                        />
                      </Stack>
                    </Grid.Col>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 6,
                      }}
                    >
                      <Stack gap={4} mb="sm">
                        <Input.Label htmlFor="cooldown_start_ts">
                          Cooldown start timestamp
                        </Input.Label>
                        <TextInput
                          type="number"
                          name="cooldown_start_ts"
                          id="cooldown_start_ts"
                          value={seletedSymbolsItem.cooldown_start_ts}
                          onChange={(e) =>
                            setSeletedSymbolsItem({
                              ...seletedSymbolsItem,
                              cooldown_start_ts: parseInt(e.target.value),
                            })
                          }
                        />
                      </Stack>
                    </Grid.Col>
                  </Grid>
                  <br />
                  <Grid>
                    <Grid.Col
                      span={{
                        base: 12,
                        md: 12,
                      }}
                    >
                      <Box
                        display="flex"
                        style={{
                          gap: 8,
                        }}
                        component="div"
                      >
                        <Button
                          color="primary"
                          onClick={() => {
                            if (seletedSymbolsItem.id !== "") {
                              updateSymbol({
                                id: seletedSymbolsItem.id,
                                symbol: seletedSymbolsItem.id,
                                blacklist_reason:
                                  seletedSymbolsItem.blacklist_reason,
                                active: seletedSymbolsItem.active,
                                cooldown: seletedSymbolsItem.cooldown,
                                cooldown_start_ts:
                                  seletedSymbolsItem.cooldown_start_ts,
                                futures_leverage:
                                  seletedSymbolsItem.futures_leverage,
                                exchange_id: seletedSymbolsItem.exchange_id,
                                base_asset: seletedSymbolsItem.base_asset,
                                quote_asset: seletedSymbolsItem.quote_asset,
                              });
                            }
                            return false;
                          }}
                          type="button"
                          mr={8}
                        >
                          Save
                        </Button>
                        <Button
                          onClick={() => {
                            setConfirmDelete(true);
                          }}
                          color="danger"
                          type="button"
                          ml={8}
                        >
                          Delete
                        </Button>
                      </Box>
                    </Grid.Col>
                  </Grid>
                </Grid.Col>
              )}
            </Grid>
          )}
        </Box>
      </Card>
      <ConfirmModal
        show={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        handleActions={async () => {
          await deleteSymbol(seletedSymbolsItem.id).unwrap();
          setConfirmDelete(false);
        }}
        primary={
          <>
            <i className="fa-solid fa-trash" />
            <VisuallyHidden>Delete</VisuallyHidden>
          </>
        }
      >
        Only use if there&apos;s a mistake in the data. Adding it in the future
        will require exchange information. Are you sure you want to delete this
        symbol? If not click the cross icon to cancel.
      </ConfirmModal>
    </div>
  );
};
export default SymbolsPage;
