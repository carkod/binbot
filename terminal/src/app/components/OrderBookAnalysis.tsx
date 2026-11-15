import { Alert, Col, Row } from "react-bootstrap";
import { getApiErrorMessage } from "../../utils/api";
import { useMicrostructureData } from "../hooks/useMicrostructureData";
import SpreadAndDepthCard from "./SpreadAndDepthCard";
import SymbolCvdCard from "./SymbolCvdCard";

const OrderBookAnalysis = ({
  enabled,
  showError = false,
}: {
  enabled: boolean;
  showError?: boolean;
}) => {
  const { symbol, liquidity, orderBookHistory } = useMicrostructureData();
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
          <SymbolCvdCard symbol={symbol} enabled={enabled} />
        </Col>
      </Row>
    </>
  );
};

export default OrderBookAnalysis;
