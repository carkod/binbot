from fastapi import APIRouter, Depends
from pydantic import ValidationError, TypeAdapter
from sqlmodel import Session
from tools.enum_definitions import Status, Strategy
from database.bot_crud import BotTableCrud
from database.utils import get_session
from bots.models import (
    BotModel,
    BotResponse,
    ErrorsRequestBody,
    BotBase,
    BotListResponse,
    IResponseBase,
    ActivePairsResponse,
)
from typing import List, Union
from tools.exceptions import BinanceErrors, BinbotErrors
from deals.margin import MarginDeal
from deals.spot import SpotLongDeal
from bots.models import BotModelResponse
from tools.handle_error import StandardResponse

bot_blueprint = APIRouter()
bot_ta = TypeAdapter(BotModelResponse)


@bot_blueprint.get("/bot", response_model=None, tags=["bots"])
def get(
    status: Status = Status.all,
    start_date: float | None = None,
    end_date: float | None = None,
    include_cooldown: bool = False,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    try:
        bots = BotTableCrud(session=session).get(
            status, start_date, end_date, include_cooldown, limit, offset
        )
        # Has to be converted to BotModel to
        # be able to serialize nested objects
        ta = TypeAdapter(list[BotModelResponse])
        data = ta.dump_python(bots)  # type: ignore
        return BotListResponse(message="Successfully found bots!", data=data)
    except ValidationError as error:
        return BotResponse(message="Failed to find bots!", data=error.json(), error=1)


@bot_blueprint.get(
    "/bot/active-pairs", response_model=ActivePairsResponse, tags=["bots"]
)
def get_active_pairs(
    session: Session = Depends(get_session),
):
    try:
        bot = BotTableCrud(session=session).get_active_pairs()
        if not bot:
            return ActivePairsResponse(message="Bot not found.", error=1, data=[])
        else:
            return ActivePairsResponse(
                message="Successfully retrieved active pairs.", data=bot
            )

    except ValidationError as error:
        return BotResponse(
            data=error.json(), error=1, message="Failed to find active pairs."
        )


@bot_blueprint.get("/bot/{id}", response_model=BotResponse, tags=["bots"])
def get_one_by_id(id: str, session: Session = Depends(get_session)):
    try:
        bot = BotTableCrud(session=session).get_one(bot_id=id)
        data = BotModelResponse.dump_from_table(bot)
        return BotResponse(message="Successfully found one bot.", data=data)
    except ValidationError as error:
        return StandardResponse(message="Bot not found.", error=1, data=error.json())
    except BinbotErrors as error:
        return StandardResponse(message=error.message, error=1)


@bot_blueprint.get("/bot/symbol/{symbol}", tags=["bots"])
def get_one_by_symbol(symbol: str, session: Session = Depends(get_session)):
    try:
        bot = BotTableCrud(session=session).get_one(bot_id=None, symbol=symbol)
        data = bot_ta.dump_python(bot)  # type: ignore
        return BotResponse(message="Successfully found one bot.", data=data)
    except ValidationError as error:
        return StandardResponse(message="Bot not found.", error=1, data=error.json())
    except BinbotErrors as error:
        return StandardResponse(message=error.message, error=1)


@bot_blueprint.post("/bot", tags=["bots"], response_model=BotResponse)
def create(
    bot_item: BotBase,
    session: Session = Depends(get_session),
):
    try:
        bot = BotTableCrud(session=session).create(bot_item)
        data = BotModelResponse.model_construct(**bot.model_dump())
        return BotResponse(message="Successfully created one bot.", data=data)
    except ValidationError as error:
        return BotResponse(message=f"Failed to create new bot {error.json()}", error=1)


@bot_blueprint.put("/bot/{id}", response_model=BotResponse, tags=["bots"])
def edit(
    id: str,
    bot_item: BotBase,
    session: Session = Depends(get_session),
):
    try:
        controller = BotTableCrud(session=session)
        bot_table = controller.get_one(id)
        # update model with ne data
        bot_table.sqlmodel_update(bot_item.model_dump())
        # client should not change deal and orders
        # these are internally generated
        transform_model = BotModel.dump_from_table(bot_table)
        bot = controller.save(transform_model)

        data = BotModelResponse.model_construct(**bot.model_dump())
        return {
            "message": "Successfully edited bot.",
            "data": data,
        }
    except ValidationError as error:
        return BotResponse(message=f"Failed to edit bot: {error.json()}", error=1)
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)


@bot_blueprint.delete("/bot", response_model=IResponseBase, tags=["bots"])
def delete(
    id: List[str],
    session: Session = Depends(get_session),
):
    """
    Delete bots, given a list of ids
    """
    try:
        BotTableCrud(session=session).delete(bot_ids=id)
        return StandardResponse(message="Sucessfully deleted bot.")
    except ValidationError as error:
        return StandardResponse(
            message="Failed to delete bot", data=error.json(), error=1
        )


@bot_blueprint.get("/bot/activate/{id}", response_model=BotResponse, tags=["bots"])
def activate_by_id(id: str, session: Session = Depends(get_session)):
    """
    Activate bot

    - Creates deal
    - If changes were made, it will override DB data
    - Because botId is received from endpoint, it will be a str not a PyObjectId
    """
    bot = BotTableCrud(session=session).get_one(bot_id=id)
    if not bot:
        return BotResponse(message="Bot not found.")

    bot_model = BotModel.dump_from_table(bot)
    if bot_model.strategy == Strategy.margin_short:
        deal_instance: Union[MarginDeal, SpotLongDeal] = MarginDeal(bot_model)
    else:
        deal_instance = SpotLongDeal(bot_model)

    try:
        data = deal_instance.open_deal()
        response_data = BotModelResponse.model_construct(**data.model_dump())
        return BotResponse(message="Successfully activated bot.", data=response_data)
    except BinbotErrors as error:
        deal_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return StandardResponse(message=error.message, error=1)
    except BinanceErrors as error:
        deal_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return StandardResponse(message=error.message, error=1)


@bot_blueprint.delete("/bot/deactivate/{id}", response_model=BotResponse, tags=["bots"])
def deactivation(id: str, session: Session = Depends(get_session)):
    """
    Deactivation means closing all deals and selling to
    fiat. This is often used to prevent losses
    """
    bot_table = BotTableCrud(session=session).get_one(bot_id=id)
    if not bot_table:
        return BotResponse(message="No active bot found.")

    bot_model = BotModel.dump_from_table(bot_table)
    if bot_model.strategy == Strategy.margin_short:
        deal_instance: Union[MarginDeal, SpotLongDeal] = MarginDeal(bot_model)
    else:
        deal_instance = SpotLongDeal(bot_model)

    try:
        data = deal_instance.close_all()
        response_data = BotModelResponse.model_construct(**data.model_dump())
        return {
            "message": "Successfully triggered panic sell! Bot deactivated.",
            "data": response_data,
        }
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)


@bot_blueprint.post("/bot/errors/{bot_id}", response_model=BotResponse, tags=["bots"])
def bot_errors(
    bot_id: str, bot_errors: ErrorsRequestBody, session: Session = Depends(get_session)
):
    """
    POST errors to a bot

    - If error(s) is received from endpoint, get it from request body
    - Else use `post_errors_by_id` method for internal calls
    """
    try:
        request_body = ErrorsRequestBody.model_dump(bot_errors)
        errors = request_body.get("errors", None)
        data = BotTableCrud(session=session).update_logs(
            log_message=errors, bot_id=bot_id
        )
        response_data = BotModelResponse.dump_from_table(data)
        return BotResponse(
            message="Errors posted successfully.", data=response_data, error=0
        )
    except ValidationError as error:
        return BotResponse(message="Failed to post errors", data=error.json(), error=1)
    except BinbotErrors as error:
        return BotResponse(message="Bot not found.", error=1, data=str(error))
