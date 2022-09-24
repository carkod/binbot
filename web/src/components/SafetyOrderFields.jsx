import {
    Button,
    Col,
    Input,
    InputGroup,
    InputGroupText,
    Label,
    Row
} from "reactstrap";

const SafetyOrderFields = ({
  safetyOrders,
  asset,
  quoteAsset,
  handleChange,
  handleBlur,
  removeSo,
}) => {
  return (
    <>
      {safetyOrders.map((e, i) => (
        <Row key={i} className="u-margin-bottom">
          <Col md="2">
            <Label htmlFor={e.name}>Name</Label>
            <p>{e.name}</p>
          </Col>
          <Col md="3" sm="10">
            <Label htmlFor={"buy_price"}>Buy price</Label>
            <InputGroup>
              <Input
                type="text"
                name={"buy_price"}
                onChange={handleChange}
                onBlur={handleBlur}
                data-index={i}
                defaultValue={e.buy_price}
                disabled={e.status > 0}
              />
              <InputGroupText>{quoteAsset || ""}</InputGroupText>
            </InputGroup>
          </Col>
          <Col md="3" sm="10">
            <Label htmlFor={"so_size"}>Buy quantity</Label>
            <InputGroup>
              <Input
                type="text"
                name={"so_size"}
                onChange={handleChange}
                onBlur={handleBlur}
                data-index={i}
                defaultValue={e.so_size}
                disabled={e.status > 0}
              />
              <InputGroupText>{asset && quoteAsset ? asset.replace(quoteAsset, "") : ""}</InputGroupText>
            </InputGroup>
          </Col>
          <Col md="2">
            <Label>Total</Label>
            <p>{(parseFloat(e.buy_price) * parseFloat(e.so_size)).toFixed(2)}</p>
          </Col>
          <Col md="1">
            <Button
              className="btn"
              color="danger"
              onClick={removeSo}
              data-index={i}
            >
              <i className="fa fa-trash" />
            </Button>
          </Col>
        </Row>
      ))}
    </>
  );
};

export default SafetyOrderFields;
