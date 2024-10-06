import { useEffect, useState, type FC } from "react"
import { Badge, Button, Container, Stack } from "react-bootstrap"
import { Col, Row } from "reactstrap"
import { botsApiSlice, useDeactivateBotMutation, useDeleteBotMutation, useGetBotsQuery } from "../../features/bots/botsApiSlice"
import { setSpinner } from "../../features/layoutSlice"
import { weekAgo } from "../../utils/time"
import BotsActions from "../components/BotsActions"
import BotsDateFilter from "../components/BotsCalendar"
import { useAppDispatch } from "../hooks"
import BotCard from "../components/BotCard"
import ConfirmModal from "../components/ConfirmModal"

export const BotsPage: FC<{}> = () => {
  const dispatch = useAppDispatch()
  const currentTs = new Date().getTime()
  const oneWeekAgo = weekAgo()
  const [removeBot, { isSuccess: botDeleted }] = useDeleteBotMutation()
  const [deactivateBot, { isSuccess: botDeactivated }] = useDeactivateBotMutation()

  // Component states
  const [selectedCards, selectCards] = useState([])
  const [botToDelete, setBotToDelete] = useState<string | null>(null)
  const [dateFilterError, setDateFilterError] = useState(null)
  const [bulkActions, setBulkActions] = useState(null)
  const [startDate, setStartDate] = useState(oneWeekAgo)
  const [endDate, setEndDate] = useState(currentTs)
  const [filterStatus, setFilterStatus] = useState("")
  const [toDelete, addToDelete] = useState([])

  // const bots = useAppSelector(state => state.bots.bots)

  const handleSelection = id => {
    let newCards = []
    if (selectedCards.includes(id)) {
      newCards = selectedCards.filter(x => x !== id)
    } else {
      newCards = selectedCards.concat(id)
    }
    selectCards(newCards)
  }
  const handleDelete = (botId: string) => {
    setBotToDelete(botId)
  }
  const confirmDelete = (index) => {
    if (index === 1) {
      removeBot([botToDelete])
    } else if (index === 2) {
      deactivateBot(botToDelete)
    }
    setBotToDelete(null)
    return false
  }
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

  const { data: props, isFetching } = useGetBotsQuery(
    { status: filterStatus, startDate, endDate },
    { refetchOnMountOrArgChange: true },
  )

  useEffect(() => {
    if (isFetching) {
      dispatch(setSpinner(true))
    }
    if (props?.bots) {
      dispatch(setSpinner(false))
    }
  }, [props, dispatch, isFetching])

  return (
    <Container>
      <Stack direction="horizontal" className="mt-3">
        <div className="p-3 gx-10">
          <h3>
            {props?.bots?.ids.length > 0 && (
              <Badge bg={props?.totalProfit > 0 ? "success" : "danger"}>
                <i className="fas fa-building-columns" />{" "}
                <span className="visually-hidden">Profit</span>
                {(props?.totalProfit || 0) + "%"}
              </Badge>
            )}
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
        {props?.bots?.ids.length > 0 ? Object.values(props?.bots?.entities).map((x, i) => (
          <Col key={i} sm="6" md="4" lg="3">
            <BotCard
              botIndex={i}
              bot={x}
              selectedCards={selectedCards}
              handleDelete={handleDelete}
              handleSelection={handleSelection}
            />
          </Col>
        )) : ""}
      </Row>
      <ConfirmModal
        show={!!botToDelete}
        handleActions={confirmDelete}
        primary={
          <>
            <i className="fa-solid fa-trash" />
            <span className="visually-hidden">Delete</span>
          </>
        }
        secondary={
          <>
            <i className="fa-solid fa-power-off" />
            <span title="Deactivate" className="visually-hidden">Deactivate</span>
          </>
        }
      >
        To close orders, please deactivate.
        Deleting will only remove the bot.
      </ConfirmModal>
    </Container>
  )
}

export default BotsPage
