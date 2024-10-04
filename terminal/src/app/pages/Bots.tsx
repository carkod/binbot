import { type FC } from "react"
import { setHeaderContent } from "../../features/layoutSlice"
import { useAppDispatch } from "../hooks"
import ConfirmModal from "../components/ConfirmModal"
import { Container } from "react-bootstrap"

export const BotsPage: FC<{}> = () => {
  const dispatch = useAppDispatch()
  const [selectedCards, setSelectedCards] = useState([])
  const [confirmModal, setConfirmModal] = useState(null)
  const [dateFilterError, setDateFilterError] = useState(null)
  const [bulkActions, setBulkActions] = useState(null)
  const [startDate, setStartDate] = useState(null)
  const [endDate, setEndDate] = useState(null)


  dispatch(setHeaderContent({
    icon: "fas fa-robot",
    headerTitle: "Bots",
  }))

  return (
    <Container>
      <div className="content">
          <Form>
            <FormGroup row>
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
                <Input
                  bsSize="sm"
                  type="select"
                  name="bulkActions"
                  id="bulk-actions"
                  onChange={this.handleChange}
                >
                  <option value="">Select bulk action</option>
                  <option value="delete-selected">Delete selected</option>
                  <option value="unselect-all">Unselect all</option>
                  <option value="completed">Show completed only</option>
                  <option value="active">Show active only</option>
                  <option value="select-all">Select all</option>
                </Input>
              </Col>
              <Col sm={2}>
                <Button onClick={this.onSubmitBulkAction}>Apply bulk action</Button>
              </Col>
              <Col sm={2}>
                <label htmlFor="startDate">Filter by start date</label>
                <Form.Control
                  type="date"
                  name="startDate"
                  ref={(element) => (this.startDate = element)}
                  onBlur={this.handleDateFilters}
                  isInvalid={!checkValue(this.state.dateFilterError)}
                />
              </Col>
              <Col sm={2}>
                <label htmlFor="endDate">Filter by end date</label>
                <Form.Control
                  type="date"
                  name="endDate"
                  onBlur={this.handleDateFilters}
                  ref={(element) => (this.endDate = element)}
                  isInvalid={!checkValue(this.state.dateFilterError)}
                />
                {!checkValue(this.state.dateFilterError) && (
                  <Form.Control.Feedback type="invalid">
                    {this.state.dateFilterError}
                  </Form.Control.Feedback>
                )}
              </Col>
            </FormGroup>
          </Form>

          <Row>
            {!checkValue(bots)
              ? bots.map((x, i) => (
                  <Col key={i} sm="6" md="4" lg="3">
                    <BotCard
                      tabIndex={i}
                      x={x}
                      selectedCards={this.state.selectedCards}
                      history={(url) => this.props.history.push(url)}
                      archiveBot={(id) => this.props.archiveBot(id)}
                      handleDelete={(id) => this.handleDelete(id)}
                      handleSelection={this.handleSelection}
                    />
                  </Col>
                ))
              : "No data available"}
          </Row>
        </div>
        <ConfirmModal
          show={() => useState({ confirmModal: null })}
          modal={this.state.confirmModal}
          handleActions={this.confirmDelete}
          acceptText={"Close"}
          cancelText={"Delete"}
        >
          Closing deals will close outstanding orders, sell coins and delete bot
        </ConfirmModal>
        {this.state.selectedCards.length > 0 && (
          <ConfirmModal>
            You did not select the items for bulk action
          </ConfirmModal>
        )}
    </Container>
  )
}

export default BotsPage
