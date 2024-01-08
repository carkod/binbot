import Badge from "react-bootstrap/Badge";
import Card from "react-bootstrap/Card";
import ListGroup from "react-bootstrap/ListGroup";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";

const computeTotalVolume = (data) => {
  const sortedData = data.toSorted((a, b) => {
    if (parseFloat(a.volume) > 0 && parseFloat(a.quoteVolume) > 0) {
      const totalVolumeA = parseFloat(a.volume) + parseFloat(a.quoteVolume);
      const totalVolumeB = parseFloat(b.volume) + parseFloat(b.quoteVolume);
      return totalVolumeA - totalVolumeB;
    }
    return 0;
  });

  return sortedData.reverse(-1).slice(0, 10);
};

const average = (data) => {
  const total = data.reduce((acc, x) => {
    return acc + parseFloat(x.quoteVolume) + parseFloat(x.volume);
  }, 0);

  return (total / data.length - 1).toLocaleString();
};

export default function VolumesRankingCard({ data, title }) {
  const sortedData = computeTotalVolume(data);
  return (
    <div>
      <Card border="success">
        <Card.Body>
          <Card.Title>{`Volume market average: ${average(data)}`}</Card.Title>
          <Card.Title>{title}</Card.Title>
          <ListGroup className="list-group-flush">
            {sortedData.map((x, i) => (
              <ListGroup.Item key={i}>
                <Row>
                  <Col>
                    <Card.Link href={`/admin/bots/new/${x.symbol}`}>
                      {x.symbol}
                    </Card.Link>
                  </Col>
                  <Col>
                    <Badge bg="success" className="u-float-right">
                      {(
                        parseFloat(x.quoteVolume) + parseFloat(x.volume)
                      ).toLocaleString()}
                    </Badge>
                  </Col>
                </Row>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Card.Body>
      </Card>
    </div>
  );
}
