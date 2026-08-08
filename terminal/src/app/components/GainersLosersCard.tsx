import { Badge, Card, ListGroup } from "react-bootstrap";
import { type GainersLosersProps } from "./GainersLosers";
import { normalizePriceChangePercent } from "../../utils/gainers-losers";
import { MarketType } from "../../utils/enums";

interface GainersLosersCardProps extends GainersLosersProps {
  title: string;
}

const GainersLosersCard = ({
  data,
  market_type,
  title,
}: GainersLosersCardProps) => {
  const getNewBotPath = (symbol: string) =>
    market_type === MarketType.FUTURES
      ? `/bots/futures/new/${symbol}`
      : `/bots/new/${symbol}`;

  return (
    <Card.Body>
      <Card.Title>{title}</Card.Title>
      <ListGroup className="list-group-flush">
        {data.map((x, i) => {
          const priceChangePercent = normalizePriceChangePercent(x);

          return (
            parseFloat(priceChangePercent) !== 0 && (
              <ListGroup.Item key={i}>
                <Card.Link href={getNewBotPath(x.symbol)}>{x.symbol}</Card.Link>
                <Badge
                  bg={parseFloat(priceChangePercent) > 0 ? "success" : "danger"}
                  className="u-float-right"
                >
                  {priceChangePercent + "%"}
                </Badge>
              </ListGroup.Item>
            )
          );
        })}
      </ListGroup>
    </Card.Body>
  );
};

export default GainersLosersCard;
