import { useState } from "react";
import { Button, Col, Form, Row } from "react-bootstrap";
import { useNavigate, useParams } from "react-router";
import { useFuturesLiquidityQuery } from "../../features/kucoinApiSlice";
import { useSymbolData } from "../hooks";
import SymbolSearch from "../components/SymbolSearch";
import OrderBookImbalanceCard from "../components/OrderBookImbalanceCard";
import { OBI_POLL_INTERVAL_MS } from "../../features/kucoinLiquidity";
import { useKucoinTradeFlow } from "../hooks/useKucoinTradeFlow";
import TradeFlowCard from "../components/TradeFlowCard";
import SpreadAndDepthCard from "../components/SpreadAndDepthCard";
import { getApiErrorMessage } from "../../utils/api";

const MicrostructureContent = ({ symbol }: { symbol: string }) => {
  const navigate = useNavigate();
  const { symbolsList } = useSymbolData();
  const [search, setSearch] = useState(symbol);
  const [validationError, setValidationError] = useState("");
  const normalizedSearch = search.trim().toUpperCase();
  const canQuery = Boolean(symbol) && normalizedSearch === symbol;
  const {
    currentData: snapshot,
    isFetching,
    isError,
    error,
    refetch,
  } = useFuturesLiquidityQuery(symbol, {
    skip: !canQuery,
    pollingInterval: OBI_POLL_INTERVAL_MS,
    skipPollingIfUnfocused: true,
    refetchOnMountOrArgChange: true,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });
  const tradeFlow = useKucoinTradeFlow(
    symbol,
    canQuery && !isError,
    snapshot?.multiplier,
  );
  const apiError =
    canQuery && isError
      ? getApiErrorMessage(error, "KuCoin symbol request failed")
      : "";
  const searchError = validationError || apiError;

  const selectSymbol = (value: string) => {
    const selected = value.trim().toUpperCase();
    if (!selected) {
      setValidationError("Enter a symbol.");
      return;
    }
    setValidationError("");
    navigate(`/microstructure/${encodeURIComponent(selected)}`);
  };

  return (
    <div className="content dashboard">
      <Form
        className="mb-4"
        onSubmit={(event) => {
          event.preventDefault();
          selectSymbol(search);
        }}
      >
        <Row className="align-items-end g-3">
          <Col>
            <SymbolSearch
              name="microstructure-symbol"
              label="Symbol"
              placeholder="Search KuCoin futures symbols"
              value={search}
              options={symbolsList}
              size="lg"
              required
              errors={
                searchError ? { "microstructure-symbol": searchError } : {}
              }
              onInputChange={(value) => {
                setSearch(value);
                setValidationError("");
              }}
              onChange={(value) => {
                setSearch(value);
                if (value) selectSymbol(value);
              }}
            />
          </Col>
          <Col xs="auto">
            <Button type="submit" size="lg">
              Search
            </Button>
          </Col>
        </Row>
      </Form>
      <Row>
        <Col md="6" xs="12">
          <OrderBookImbalanceCard
            snapshot={snapshot}
            enabled={canQuery}
            isFetching={isFetching}
            isError={isError}
            onRetry={() => refetch()}
          />
        </Col>
        <Col md="6" xs="12">
          <TradeFlowCard
            kind="cvd"
            buckets={tradeFlow.history.buckets}
            enabled={canQuery}
            status={tradeFlow.status}
            restarted={tradeFlow.restarted}
            storageError={tradeFlow.storageError}
          />
        </Col>
      </Row>
      <Row>
        <Col xs="12">
          <SpreadAndDepthCard
            snapshot={snapshot}
            enabled={canQuery}
            isFetching={isFetching}
            isError={isError}
            onRetry={() => refetch()}
          />
        </Col>
      </Row>
    </div>
  );
};

const MicrostructurePage = () => {
  const { symbol = "" } = useParams<{ symbol: string }>();
  const normalizedSymbol = symbol.trim().toUpperCase();
  return (
    <MicrostructureContent key={normalizedSymbol} symbol={normalizedSymbol} />
  );
};

export default MicrostructurePage;
