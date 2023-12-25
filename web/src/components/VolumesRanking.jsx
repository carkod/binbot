import Badge from "react-bootstrap/Badge";
import Card from "react-bootstrap/Card";
import ListGroup from "react-bootstrap/ListGroup";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";

const computeProportions = (data) => {
  let total = {
    gainerCount: 0,
    gainerAccumulator: 0,
    loserAccumulator: 0,
    loserCount: 0,
  };
  data.reduce((c, a) => {
    if (parseFloat(a.volume) > 0) {
      total.gainerAccumulator =
        c.gainerAccumulator + parseFloat(a.volume);
      total.gainerCount++;
      return total;
    } else {
      total.loserAccumulator =
      c.loserAccumulator + parseFloat(a.volume);
      total.loserCount++;
      return total;
    }
  }, total);

  return total;
};


const GainersLosersCard = ({ data, title }) => {
  return (
    <>
      <Card.Body>
        <Card.Title>{title}</Card.Title>
        <ListGroup className="list-group-flush">
          {data.map((x, i) => (
            <ListGroup.Item key={i}>
              <Card.Link href={`/admin/bots/new/${x.symbol}`}>
                {x.symbol}
              </Card.Link>
              <Badge
                bg={parseFloat(x.priceChangePercent) > 0 ? "success" : "danger"}
                className="u-float-right"
              >
                {x.priceChangePercent + "%"}
              </Badge>
            </ListGroup.Item>
          ))}
        </ListGroup>
      </Card.Body>
    </>
  );
};

export default function VolumesRanking({ data }) {
  const totalVolume = computeTotalVolume(data);
  // Top 10
  const gainersData = data.slice(0, 10);
  const perGainers = ((gainerCount / data.length) * 100).toFixed(2) + "%";
  // Bottom 10
  const losersData = data.slice(-10).reverse();
  const perLosers = ((loserCount / data.length) * 100).toFixed(2) + "%";
  return (
    <div>
      <Card border="success">
        <div className="p-line-chart">
          <div className="p-line-chart__box">
            <div className="p-line-chart--left" style={{ width: perGainers }}>
              <span>{gainerAccumulator.toFixed(2)}</span>
            </div>
            <div className="p-line-chart--right" style={{ width: perLosers }}>
              <span>{loserAccumulator.toFixed(2)}</span>
            </div>
          </div>
          <div className="p-line-chart--legend">
            <div>
              Gainers: <span>{perGainers}</span>
            </div>
            <div>
              Losers: <span>{perLosers}</span>
            </div>
          </div>
        </div>

        <Row>
          <Col>
            <GainersLosersCard
              data={gainersData}
              title="Today's gainers in USDT market"
            />
          </Col>
          <Col>
            <GainersLosersCard
              data={losersData}
              title="Today's losers in USDT market"
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
}
