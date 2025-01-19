import { Badge, Card, ListGroup } from "react-bootstrap";

const GainersLosersCard = ({ data, title }) => {
  return (
    <Card.Body>
      <Card.Title>{title}</Card.Title>
      <ListGroup className="list-group-flush">
        {data.map(
          (x, i) =>
            parseFloat(x.priceChangePercent) !== 0 && (
              <ListGroup.Item key={i}>
                <Card.Link href={`/bots/new/${x.symbol}`}>{x.symbol}</Card.Link>
                <Badge
                  bg={
                    parseFloat(x.priceChangePercent) > 0 ? "success" : "danger"
                  }
                  className="u-float-right"
                >
                  {x.priceChangePercent + "%"}
                </Badge>
              </ListGroup.Item>
            ),
        )}
      </ListGroup>
    </Card.Body>
  );
};

export default GainersLosersCard;
