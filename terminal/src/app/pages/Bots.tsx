import { useEffect, useState, type FC } from "react"
import { Badge, Button, Col, Container, Form, Stack } from "react-bootstrap"
import { Row } from "reactstrap"
import { setHeaderContent, setSpinner } from "../../features/layoutSlice"
import BotsActions from "../components/BotsActions"
import BotsDateFilter from "../components/BotsCalendar"
import ConfirmModal from "../components/ConfirmModal"
import { useAppDispatch, useAppSelector } from "../hooks"
import BotCard from "../components/BotCard"
import {
  botsApiSlice,
  useDeleteBotMutation,
  useGetBotsQuery,
} from "../../features/bots/botsApiSlice"
import { weekAgo } from "../../utils/time"

export const BotsPage: FC<{}> = () => {
  const dispatch = useAppDispatch()
  const currentTs = new Date().getTime()
  const oneWeekAgo = weekAgo()
  // const [id, { isFetching, isSuccess: botDeleted }] = useDeleteBotMutation()

  // Component states
  const [selectedCards, selectCards] = useState([])
  const [confirmModal, setConfirmModal] = useState(null)
  const [dateFilterError, setDateFilterError] = useState(null)
  const [bulkActions, setBulkActions] = useState(null)
  const [startDate, setStartDate] = useState(oneWeekAgo)
  const [endDate, setEndDate] = useState(currentTs)
  const [filterStatus, setFilterStatus] = useState("")

  const { data, isSuccess } = useGetBotsQuery({
    status: "",
    startDate: oneWeekAgo,
    endDate: currentTs,
  })

  const handleSelection = id => {
    const index = selectedCards.indexOf(id)
    if (index > -1) {
      selectedCards.splice(index, 1)
    } else {
      selectedCards.push(id)
    }
    selectCards(selectedCards)
  }
  const handleDelete = id => {}
  const confirmDelete = () => {}
  const onSubmitBulkAction = () => {}
  const handleStartDate = ts => {
    setStartDate(ts)
    if (ts > endDate) {
      setDateFilterError("Start date cannot be greater than end date")
    } else {
      setDateFilterError(null)
      dispatch(
        botsApiSlice.endpoints.getBots.initiate({
          status: filterStatus,
          startDate: ts,
          endDate: endDate,
        }),
      )
    }
  }
  const handleEndDate = ts => {
    setEndDate(ts)
    if (ts < startDate) {
      setDateFilterError("End date cannot be less than start date")
    } else {
      setDateFilterError(null)
      dispatch(
        botsApiSlice.endpoints.getBots.initiate({
          status: filterStatus,
          startDate: startDate,
          endDate: ts,
        }),
      )
    }
  }

  useEffect(() => {
    if (data) {
      console.log("data useEffect", data)
    }
  }, [data, isSuccess])

  return (
    <Container>
      {console.log("isSuccess", isSuccess)}
      {console.log("data", data)}
      <Stack gap={3} direction="horizontal" className="mt-3">
        <div className="p-3 gx-10">
          <h3>
            Profit
            {/* <Badge
                    color={totalProfit > 0 ? "success" : "danger"}
                  >
                    <i className="nc-icon nc-bank" />{" "}
                    {(totalProfit || 0) + "%"}
                  </Badge> */}
          </h3>
        </div>
        <div className="p-3">
          <BotsActions
            defaultValue={bulkActions}
            handleChange={setBulkActions}
          />
        </div>
        <div className="p-3">
          <Button onClick={onSubmitBulkAction}>Apply bulk action</Button>
        </div>
        <div className="p-3">
          <BotsDateFilter
            title="Filter by start date"
            controlId="startDate"
            selectedDate={startDate}
            handleDateChange={handleStartDate}
          />
        </div>
        <div className="p-3">
          <BotsDateFilter
            title="Filter by end date"
            controlId="endDate"
            selectedDate={endDate}
            handleDateChange={handleEndDate}
          />
        </div>
      </Stack>
      <Row>
        {/* {data?.map((x, i) => (
          <Col key={i} sm="6" md="4" lg="3">
            <BotCard
              botIndex={i}
              bot={x}
              selectedCards={selectedCards}
              // handleDelete={(id) => deleteBot(id)}
              // handleSelection={this.handleSelection}
            />
          </Col>
        ))} */}
      </Row>
      <ConfirmModal
        close={!!confirmModal}
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
