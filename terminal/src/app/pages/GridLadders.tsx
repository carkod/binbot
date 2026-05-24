import { useContext, useEffect, useMemo, useState, type FC } from "react";
import {
  AlertHeading,
  Badge,
  Button,
  Col,
  Container,
  Form,
  Row,
  Stack,
} from "react-bootstrap";
import ConfirmModal from "../components/ConfirmModal";
import GridLadderCard from "../components/GridLadderCard";
import { SpinnerContext } from "../Layout";
import {
  GridLadderStatus,
  isActiveGridLadder,
  type GridLadder,
} from "../../features/gridLadders/gridLadders";
import {
  useCloseGridLadderMutation,
  useGetActiveGridLaddersQuery,
  useGetGridLaddersQuery,
} from "../../features/gridLadders/gridLaddersApiSlice";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";

const GridLaddersPage: FC = () => {
  const { setSpinner } = useContext(SpinnerContext);
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [ladderToClose, setLadderToClose] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [symbolState, setSymbolState] = useState<string>("");
  const [showActiveOnly, setShowActiveOnly] = useState<boolean>(false);

  const {
    data: allLadders = [],
    isFetching,
    refetch,
  } = useGetGridLaddersQuery(
    { limit: 100, offset: 0 },
    { refetchOnFocus: true },
  );
  const { data: autotradeSettings } = useGetSettingsQuery();
  const { data: activeLadders = [] } = useGetActiveGridLaddersQuery(undefined, {
    skip: !showActiveOnly,
    refetchOnFocus: true,
    pollingInterval: showActiveOnly ? 10000 : 0,
  });

  const [closeGridLadder, { isLoading: isClosing }] =
    useCloseGridLadderMutation();

  const fiat = autotradeSettings?.fiat ?? "fiat";
  const sourceLadders = showActiveOnly ? activeLadders : allLadders;

  const filteredLadders = useMemo(() => {
    return sourceLadders.filter((ladder) => {
      const statusMatches =
        filterStatus === "all" || ladder.status === filterStatus;
      const symbolMatches =
        !symbolState ||
        ladder.symbol.toLowerCase().includes(symbolState.toLowerCase());
      return statusMatches && symbolMatches;
    });
  }, [sourceLadders, filterStatus, symbolState]);

  const summary = useMemo(() => {
    return filteredLadders.reduce(
      (acc, ladder) => {
        acc.active += isActiveGridLadder(ladder.status) ? 1 : 0;
        acc.reserved += ladder.reserved_margin;
        acc.used += ladder.used_margin;
        acc.realized += ladder.realized_pnl;
        acc.unrealized += ladder.unrealized_pnl;
        acc.openLevels += ladder.levels.filter(
          (level) => level.entry_order_id || level.take_profit_order_id,
        ).length;
        return acc;
      },
      {
        active: 0,
        reserved: 0,
        used: 0,
        realized: 0,
        unrealized: 0,
        openLevels: 0,
      },
    );
  }, [filteredLadders]);

  useEffect(() => {
    setSpinner(isFetching || isClosing);
  }, [isFetching, isClosing, setSpinner]);

  const handleSelect = (id: string) => {
    setSelectedCards((prev) =>
      prev.includes(id)
        ? prev.filter((cardId) => cardId !== id)
        : prev.concat(id),
    );
  };

  const confirmClose = async (action: number) => {
    if (action !== 1 || !ladderToClose) {
      setLadderToClose(null);
      return;
    }

    await closeGridLadder({
      id: ladderToClose,
      reason: "manual_close",
    }).unwrap();
    setSelectedCards([]);
    setLadderToClose(null);
    await refetch();
  };

  return (
    <Container fluid>
      <Stack direction="horizontal" gap={4} className="flex-wrap">
        <AlertHeading>
          <Badge bg={summary.realized >= 0 ? "success" : "danger"}>
            Realized PnL: {summary.realized.toFixed(4)}
          </Badge>
        </AlertHeading>
        <AlertHeading>
          <Badge bg={summary.unrealized >= 0 ? "success" : "danger"}>
            Unrealized PnL: {summary.unrealized.toFixed(4)}
          </Badge>
        </AlertHeading>
        <AlertHeading>
          <Badge bg="success">Active ladders: {summary.active} / 3</Badge>
        </AlertHeading>
        <AlertHeading>
          <Badge bg="secondary">
            Reserved margin: {summary.reserved.toFixed(2)} {fiat}
          </Badge>
        </AlertHeading>
        <AlertHeading>
          <Badge bg="secondary">
            Used margin: {summary.used.toFixed(2)} {fiat}
          </Badge>
        </AlertHeading>
        <AlertHeading>
          <Badge bg="info">Open levels: {summary.openLevels}</Badge>
        </AlertHeading>
      </Stack>

      <hr />

      <Row className="mb-3">
        <Col md={3}>
          <Form.Control
            placeholder="Search by symbol"
            value={symbolState}
            onChange={(e) => setSymbolState(e.target.value)}
          />
        </Col>
        <Col md={3}>
          <Form.Select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All statuses</option>
            {Object.values(GridLadderStatus).map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Form.Select>
        </Col>
        <Col md={3}>
          <Form.Check
            type="switch"
            id="active-only"
            checked={showActiveOnly}
            onChange={(e) => setShowActiveOnly(e.target.checked)}
            label="Show active only"
          />
        </Col>
        <Col md={3}>
          <Button
            variant="outline-secondary"
            onClick={() =>
              setSelectedCards(
                filteredLadders.map((ladder: GridLadder) => ladder.id),
              )
            }
          >
            Select all
          </Button>{" "}
          <Button
            variant="outline-secondary"
            onClick={() => setSelectedCards([])}
          >
            Unselect all
          </Button>
        </Col>
      </Row>

      {filteredLadders.length === 0 ? (
        <p>
          {showActiveOnly
            ? "No active grid ladders"
            : "No grid ladders deployed yet"}
        </p>
      ) : (
        <Row>
          {filteredLadders.map((ladder) => (
            <Col key={ladder.id} lg={4} className="mb-3">
              <GridLadderCard
                ladder={ladder}
                selected={selectedCards.includes(ladder.id)}
                onSelect={handleSelect}
                onClose={setLadderToClose}
              />
            </Col>
          ))}
        </Row>
      )}

      <ConfirmModal
        show={Boolean(ladderToClose)}
        handleActions={confirmClose}
        primary="Close ladder"
      >
        Closing a grid ladder should cancel open grid orders and stop the
        ladder. If positions are open, backend close behavior depends on the
        grid manager state.
      </ConfirmModal>
    </Container>
  );
};

export default GridLaddersPage;
