from fastapi import APIRouter, Depends
from pydantic import ValidationError, TypeAdapter
from sqlmodel import Session
from tools.enum_definitions import Status
from databases.crud.bot_crud import BotTableCrud
from databases.utils import get_session
from bots.models import (
    BotModel,
    BotResponse,
    ErrorsRequestBody,
    BotBase,
    BotListResponse,
    IResponseBase,
)
from typing import List, Optional
from tools.exceptions import BinanceErrors, BinbotErrors
from bots.models import BotModelResponse
from tools.handle_error import StandardResponse
from deals.gateway import DealGateway
from databases.tables.bot_table import BotTable
from kucoin_universal_sdk.model.common import RestError

bot_blueprint = APIRouter()
bot_ta = TypeAdapter(BotModelResponse)


@bot_blueprint.get("/bot", response_model=BotListResponse, tags=["bots"])
def get(
    status: Status = Status.all,
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    try:
        bots = BotTableCrud(session=session).get(
            status, start_date, end_date, limit, offset
        )
        # Has to be converted to BotModel to
        # be able to serialize nested objects
        ta = TypeAdapter(list[BotModelResponse])
        data = ta.dump_python(bots)  # type: ignore
        return BotListResponse(message="Successfully found bots!", data=data)
    except ValidationError as error:
        return BotResponse(message="Failed to find bots!", data=error.json(), error=1)


@bot_blueprint.get("/bot/active-pairs", response_model=BotListResponse, tags=["bots"])
def get_active_pairs(session: Session = Depends(get_session)):
    """
    Get pairs/symbols that have active bots
    and cooldown bots (bots we don't want to open for a while)
    """
    try:
        data = BotTableCrud(session=session).get_active_pairs()
        return BotListResponse(message="Successfully found active pairs.", data=data)
    except ValidationError as error:
        return BotResponse(
            message="Failed to find active pairs.", data=error.json(), error=1
        )
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)


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
        return BotResponse(message="Sucessfully deleted bot.")
    except ValidationError as error:
        return BotResponse(message="Failed to delete bot", data=error.json(), error=1)


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
    deal_instance = DealGateway(bot_model, db_table=BotTable)

    try:
        data = deal_instance.open_deal()
        response_data = BotModelResponse.model_validate(data.model_dump())
        message = "Successfully activated bot."
        if bot.status == Status.active:
            message = "Successfully updated bot."

        return BotResponse(message=message, data=response_data)
    except BinbotErrors as error:
        deal_instance.update_logs(message=error.message)
        return BotResponse(data=bot_model, message=error.message, error=1)
    except BinanceErrors as error:
        deal_instance.update_logs(message=error.message)
        return BotResponse(data=bot_model, message=error.message, error=1)
    except RestError as error:
        message = error.response.message if error.response else str(error)
        deal_instance.update_logs(message=message)
        return BotResponse(data=bot_model, message=message, error=1)


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
    deal_instance = DealGateway(bot_model, db_table=BotTable)

    try:
        data = deal_instance.deactivation()
        response_data = BotModelResponse.model_construct(**data.model_dump())
        return {
            "message": "Successfully triggered panic sell! Bot deactivated.",
            "data": response_data,
        }
    except BinbotErrors as error:
        return BotResponse(data=response_data, message=error.message, error=1)


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
        errors = request_body.get("errors", [])
        bot_table = BotTableCrud(session=session).get_one(bot_id=bot_id)
        bot_model = BotModel.dump_from_table(bot_table)
        if not bot_model:
            return BotResponse(message="Bot not found.", error=1)

        data = BotTableCrud(session=session).update_logs(
            log_message=errors, bot=bot_model
        )
        response_data = BotModelResponse.dump_from_table(data)
        return BotResponse(
            message="Errors posted successfully.", data=response_data, error=0
        )
    except ValidationError as error:
        return BotResponse(message="Failed to post errors", data=error.json(), error=1)
    except BinbotErrors as error:
        return BotResponse(message="Bot not found.", error=1, data=str(error))
