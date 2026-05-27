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
import BotsDateFilter from "../components/BotsCalendar";
import ConfirmModal from "../components/ConfirmModal";
import GridLadderCard from "../components/GridLadderCard";
import { SpinnerContext } from "../Layout";
import {
  GridLadderStatus,
  isActiveGridLadder,
  calculateLevelPnlSum,
  type GridLadder,
} from "../../features/gridLadders/gridLadders";
import {
  useCloseGridLadderMutation,
  useDeleteGridLadderMutation,
  useGetGridLaddersQuery,
} from "../../features/gridLadders/gridLaddersApiSlice";
import { useGetSettingsQuery } from "../../features/autotradeApiSlice";
import { calculateGridReturnPct } from "../../utils/grid-ladder";
import { weekAgo } from "../../utils/time";

const GridLaddersPage: FC = () => {
  const { setSpinner } = useContext(SpinnerContext);
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [ladderToClose, setLadderToClose] = useState<string | null>(null);
  const [ladderToDelete, setLadderToDelete] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [symbolState, setSymbolState] = useState<string>("");
  const [startDate, setStartDate] = useState<number>(weekAgo());
  const [endDate, setEndDate] = useState<number>(new Date().getTime());

  const {
    data: allLadders = [],
    isFetching,
    refetch,
  } = useGetGridLaddersQuery(
    { limit: 100, offset: 0, startDate, endDate },
    { refetchOnFocus: true },
  );
  const { data: autotradeSettings } = useGetSettingsQuery();

  const [closeGridLadder, { isLoading: isClosing }] =
    useCloseGridLadderMutation();
  const [deleteGridLadder, { isLoading: isDeleting }] =
    useDeleteGridLadderMutation();

  const fiat = autotradeSettings?.fiat ?? "fiat";

  const filteredLadders = useMemo(() => {
    return allLadders.filter((ladder) => {
      const statusMatches =
        filterStatus === "all" || ladder.status === filterStatus;
      const symbolMatches =
        !symbolState ||
        ladder.symbol.toLowerCase().includes(symbolState.toLowerCase());
      return statusMatches && symbolMatches;
    });
  }, [allLadders, filterStatus, symbolState]);

  const summary = useMemo(() => {
    return filteredLadders.reduce(
      (acc, ladder) => {
        acc.active += isActiveGridLadder(ladder.status) ? 1 : 0;
        acc.reserved += ladder.reserved_margin;
        // Active ladders keep realized_pnl=0 until close; surface TP-cycle
        // profits from individual levels so the summary isn't misleadingly 0.
        const levelPnl = isActiveGridLadder(ladder.status)
          ? calculateLevelPnlSum(ladder)
          : 0;
        acc.realized += ladder.realized_pnl + levelPnl;
        acc.unrealized += ladder.unrealized_pnl;
        acc.openLevels += ladder.levels.filter(
          (level) => level.entry_order_id || level.take_profit_order_id,
        ).length;
        return acc;
      },
      {
        active: 0,
        reserved: 0,
        realized: 0,
        unrealized: 0,
        openLevels: 0,
      },
    );
  }, [filteredLadders]);

  useEffect(() => {
    setSpinner(isFetching || isClosing || isDeleting);
  }, [isFetching, isClosing, isDeleting, setSpinner]);

  const handleSelect = (id: string) => {
    setSelectedCards((prev) =>
      prev.includes(id)
        ? prev.filter((cardId) => cardId !== id)
        : prev.concat(id),
    );
  };

  const confirmDelete = async (action: number) => {
    if (action !== 1 || !ladderToDelete) {
      setLadderToDelete(null);
      return;
    }
    // Capture id and clear state immediately so the modal closes before the
    // request completes (and even if unwrap() throws).
    const id = ladderToDelete;
    setLadderToDelete(null);
    try {
      await deleteGridLadder(id).unwrap();
    } finally {
      // invalidatesTags handles cache, but refetch ensures the list updates
      // even if the tag subscription has a timing gap.
      await refetch();
    }
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
          <Badge bg="info">Open levels: {summary.openLevels}</Badge>
        </AlertHeading>
      </Stack>

      <hr />

      <Row className="mb-3 g-2 align-items-end">
        <Col md={2}>
          <Form.Control
            placeholder="Search by symbol"
            value={symbolState}
            onChange={(e) => setSymbolState(e.target.value)}
          />
        </Col>
        <Col md={2}>
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
        <Col md={2}>
          <BotsDateFilter
            title="Start date"
            controlId="gridStartDate"
            selectedDate={startDate}
            handleDateChange={setStartDate}
          />
        </Col>
        <Col md={2}>
          <BotsDateFilter
            title="End date"
            controlId="gridEndDate"
            selectedDate={endDate}
            handleDateChange={setEndDate}
          />
        </Col>
        <Col md="auto">
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

      <hr />

      {filteredLadders.length === 0 ? (
        <p>No grid ladders deployed yet</p>
      ) : (
        <Row>
          {filteredLadders.map((ladder) => {
            const gridReturnPct = calculateGridReturnPct(ladder);

            return (
              <Col key={ladder.id} lg={4} className="mb-3">
                <GridLadderCard
                  ladder={ladder}
                  gridReturnPct={gridReturnPct}
                  selected={selectedCards.includes(ladder.id)}
                  onSelect={handleSelect}
                  onClose={setLadderToClose}
                  onDelete={setLadderToDelete}
                />
              </Col>
            );
          })}
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

      <ConfirmModal
        show={Boolean(ladderToDelete)}
        handleActions={confirmDelete}
        primary="Delete record"
      >
        This permanently deletes the ladder record and all associated levels and
        orders from the database. It does not cancel exchange orders or close
        positions — only use this to clean up local records.
      </ConfirmModal>
    </Container>
  );
};

export default GridLaddersPage;
