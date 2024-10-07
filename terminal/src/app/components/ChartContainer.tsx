import { Badge, Card, Col, Row } from "react-bootstrap"

export const ChartContainer = () => {
  return (
    <Card style={{ minHeight: "650px" }}>
      <Card.Header>
        <Row style={{ alignItems: "baseline" }}>
          <Col>
            <Card.Title tag="h3">
              {this.props.bot?.pair}{" "}
              <Badge
                color={
                  parseFloat(this.props.bot_profit) > 0 ? "success" : "danger"
                }
              >
                {this.props.bot_profit ? this.props.bot_profit + "%" : "0%"}
              </Badge>{" "}
              {!checkValue(this.props.bot?.status) && (
                <Badge
                  color={
                    this.props.bot.status === "active"
                      ? "success"
                      : this.props.bot.status === "error"
                        ? "warning"
                        : this.props.bot.status === "completed"
                          ? "info"
                          : "secondary"
                  }
                >
                  {this.props.bot.status}
                </Badge>
              )}{" "}
              {!checkValue(this.props.bot.strategy) && (
                <Badge color="info">{this.props.bot.strategy}</Badge>
              )}
            </CardTitle>
          </Col>
          <Col>
            {!checkValue(this.props.bot_profit) &&
              !isNaN(this.props.bot_profit) && (
                <h4>
                  Earnings after commissions (est.):{" "}
                  {roundDecimals(parseFloat(this.props.bot_profit) - 0.3) + "%"}
                </h4>
              )}
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {!checkValue(this.props.bot?.pair) && (
          <TVChartContainer
            symbol={this.props.bot.pair}
            interval={this.state.interval}
            timescaleMarks={updateTimescaleMarks(this.props.bot)}
            orderLines={this.state.currentOrderLines}
            onTick={tick => this.updatedPrice(tick.close)}
            getLatestBar={bar => this.handleInitialPrice(bar[3])}
          />
        )}
      </Card.Body>
    </Card>
  )
}
