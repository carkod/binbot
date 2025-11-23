import React, { type FC, useEffect, useState } from "react";
import { Button, Card, Col, Row, Form } from "react-bootstrap";
import SymbolSearch from "../components/SymbolSearch";
import {
  type SymbolRequestPayload,
  useDeleteSymbolMutation,
  useUpdateSymbolMutation,
  useGetSymbolsQuery,
} from "../../features/symbolsApiSlice";
import LightSwitch from "../components/LightSwitch";
import { type FieldValues, useForm } from "react-hook-form";
import ConfirmModal from "../components/ConfirmModal";

const SymbolsPage: FC = () => {
  const { data: symbols } = useGetSymbolsQuery();
  const [updateSymbol] = useUpdateSymbolMutation();
  const [deleteSymbol] = useDeleteSymbolMutation();
  const [symbolsList, setSymbolsList] = useState<string[]>([]);

  const [seletedSymbolsItem, setSeletedSymbolsItem] = useState<SymbolRequestPayload>({
    id: "",
    blacklist_reason: "",
    active: true,
    cooldown: 0,
    cooldown_start_ts: 0,
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

  return (
    <div className="content">
      <Card>
        <Card.Header>
          <Card.Title>Symbols</Card.Title>
        </Card.Header>
        <Card.Body>
          {symbols && symbols.length > 0 && (
            <Row>
              <Col md="6">
                <SymbolSearch
                  name="pair"
                  label="Select pair"
                  options={symbolsList}
                  required
                  errors={errors}
                  onBlur={(e) => {
                    const symbol = symbols.find((s) => s.id === e.target.value);
                    if (symbol) {
                      setSeletedSymbolsItem({
                        id: symbol.id,
                        blacklist_reason: symbol.blacklist_reason,
                        active: symbol.active,
                        cooldown: symbol.cooldown,
                        cooldown_start_ts: symbol.cooldown_start_ts,
                      });
                    }
                  }}
                />
              </Col>
              {symbolsList && seletedSymbolsItem.id !== "" && (
                <Col md="6">
                  <Row>
                    <Col md="4">
                      <Form.Group>
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
                      </Form.Group>
                    </Col>
                    <Col md="8">
                      <Form.Group>
                        <label htmlFor="blacklist_reason">
                          Blacklisted reason
                        </label>
                        <Form.Control
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
                      </Form.Group>
                    </Col>
                  </Row>
                  <br />
                  <Row>
                    <Col md="6">
                      <Form.Group>
                        <Form.Label htmlFor="cooldown">Cooldown</Form.Label>
                        <Form.Control
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
                      </Form.Group>
                    </Col>
                    <Col md="6">
                      <Form.Group>
                        <Form.Label htmlFor="cooldown_start_ts">
                          Cooldown start timestamp
                        </Form.Label>
                        <Form.Control
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
                      </Form.Group>
                    </Col>
                  </Row>
                  <br />
                  <Row>
                    <Col md="12">
                      <div className="d-flex gap-2">
                        <Button
                          color="primary"
                          className="mr-2"
                          onClick={() => {
                            if (seletedSymbolsItem.id !== "") {
                              updateSymbol({
                                id: seletedSymbolsItem.id,
                                blacklist_reason:
                                  seletedSymbolsItem.blacklist_reason,
                                active: seletedSymbolsItem.active,
                                cooldown: seletedSymbolsItem.cooldown,
                                cooldown_start_ts:
                                  seletedSymbolsItem.cooldown_start_ts,
                              });
                            }
                            return false;
                          }}
                        >
                          Save
                        </Button>
                        <Button
                          className="ml-2"
                          variant="danger"
                          onClick={() => {
                            setConfirmDelete(true);
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </Col>
                  </Row>
                </Col>
              )}
            </Row>
          )}
        </Card.Body>
      </Card>
      <ConfirmModal
        show={confirmDelete}
        handleActions={() => deleteSymbol(seletedSymbolsItem.id)}
        primary={
          <>
            <i className="fa-solid fa-trash" />
            <span className="visually-hidden">Delete</span>
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
