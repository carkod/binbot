import { Alert, Col, Row } from "react-bootstrap";
import { getApiErrorMessage } from "../../utils/api";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import SpreadAndDepthCard from "./SpreadAndDepthCard";
import TradeFlowCard from "./TradeFlowCard";

const OrderBookAnalysis = ({
  enabled,
  showError = false,
}: {
  enabled: boolean;
  showError?: boolean;
}) => {
  const { liquidity, tradeFlow, orderBookHistory } = useMicrostructureData();
  const { isFetching, isError, error, refetch } = liquidity;

  return (
    <>
      {enabled && showError && isError && (
        <Alert variant="danger">
          {getApiErrorMessage(error, "KuCoin symbol request failed")}
        </Alert>
      )}
      <Row>
        <Col md="6" xs="12">
          <SpreadAndDepthCard
            orderBookHistory={orderBookHistory}
            enabled={enabled}
            isFetching={isFetching}
            isError={isError}
            onRetry={() => refetch()}
          />
        </Col>
        <Col md="6" xs="12">
          <TradeFlowCard
            kind="cvd"
            buckets={tradeFlow.history.buckets}
            enabled={enabled}
            status={tradeFlow.status}
            restarted={tradeFlow.restarted}
            storageError={tradeFlow.storageError}
          />
        </Col>
      </Row>
    </>
  );
};

export default OrderBookAnalysis;
