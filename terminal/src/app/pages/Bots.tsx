import { useState, type FC } from "react"
import { Badge, Button, Col, Container, Form } from "react-bootstrap"
import { Row } from "reactstrap"
import { setHeaderContent } from "../../features/layoutSlice"
import BotsActions from "../components/BotsActions"
import BotsDateFilter from "../components/BotsCalendar"
import ConfirmModal from "../components/ConfirmModal"
import { useAppDispatch } from "../hooks"

export const BotsPage: FC<{}> = () => {
  const dispatch = useAppDispatch()
  const [selectedCards, setSelectedCards] = useState([])
  const [confirmModal, setConfirmModal] = useState(null)
  const [dateFilterError, setDateFilterError] = useState(null)
  const [bulkActions, setBulkActions] = useState(null)
  const [startDate, setStartDate] = useState(null)
  const [endDate, setEndDate] = useState(null)

  const handleChange = (e) => {}
  const handleSelection = (id) => {}
  const handleDelete = (id) => {}
  const confirmDelete = () => {}
  const onSubmitBulkAction = () => {}
  const handleStartDate = (e) => {}
  const handleEndDate = (e) => {}


  dispatch(setHeaderContent({
    icon: "fas fa-robot",
    headerTitle: "Bots",
  }))

  return (
    <Container>
      <Row>
        <Col>
          <Form>
            <Form.Group>
              <Col sm={2}>
                <h3>
                  <Badge
                    color={this.props.totalProfit > 0 ? "success" : "danger"}
                  >
                    <i className="nc-icon nc-bank" />{" "}
                    {(this.props.totalProfit || 0) + "%"}
                  </Badge>
                </h3>
              </Col>
              <Col sm={2}>
                <BotsActions defaultValue={bulkActions} handleChange={setBulkActions} />
              </Col>
              <Col sm={2}>
                <Button onClick={onSubmitBulkAction}>Apply bulk action</Button>
              </Col>
              <Col sm={2}>
                <BotsDateFilter selectedDate={startDate} handleDateChange={handleStartDate} />
              </Col>
              <Col sm={2}>
                <BotsDateFilter selectedDate={endDate} handleDateChange={handleEndDate} />
              </Col>
            </FormGroup>
          </Form>
          </Col>
          </Row>
          <Row>
            {bots?.map((x, i) => (
                  <Col key={i} sm="6" md="4" lg="3">
                    <BotCard
                      tabIndex={i}
                      x={x}
                      selectedCards={selectedCards}
                      history={(url) => this.props.history.push(url)}
                      archiveBot={(id) => this.props.archiveBot(id)}
                      handleDelete={(id) => this.handleDelete(id)}
                      handleSelection={this.handleSelection}
                    />
                  </Col>
                ))
              : "No data available"}
          </Row>
        <ConfirmModal
          show={confirmModal !== null}
          modal={confirmModal}
          handleActions={confirmDelete}
          acceptText={"Close"}
          cancelText={"Delete"}
        >
          Closing deals will close outstanding orders, sell coins and delete bot
        </ConfirmModal>
    </Container>
  )
}

export default BotsPage
