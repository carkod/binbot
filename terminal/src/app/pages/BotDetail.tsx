import type { FC } from "react"
import { useEffect } from "react"
import { Form } from "react-bootstrap"
import { useForm } from "react-hook-form"
import { type LoginFormState } from "../components/LoginForm"
import { useLocation, useParams } from "react-router"
import MainTabs from "../components/MainTabs"
import { useGetBotsQuery, useGetSingleBotQuery } from "../../features/bots/botsApiSlice"

export const BotDetail: FC<{}> = () => {
  const { id } = useParams()

  const { data: bot } = useGetSingleBotQuery(id)

  useEffect(() => {
    if (bot) {
      console.log(bot)
    }
  }, [bot])

  return (
    <div className="content">
      <div>Candlestick graph here</div>
      {/* <MainTabs bot={} /> */}
    </div>
  )
}

export default BotDetail
