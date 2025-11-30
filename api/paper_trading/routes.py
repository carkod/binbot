from fastapi import APIRouter, Depends
from sqlmodel import Session
from pydantic import TypeAdapter, ValidationError
from deals.gateway import DealGateway
from tools.enum_definitions import Status
from databases.tables.bot_table import PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.utils import get_session
from tools.exceptions import BinanceErrors, BinbotErrors
from tools.handle_error import api_response, StandardResponse
from bots.models import BotModel, BotResponse, BotListResponse, BotBase, BotPairsList
from typing import List, Optional
from bots.models import BotModelResponse, ErrorsRequestBody


paper_trading_blueprint = APIRouter()
ta = TypeAdapter(list[BotModelResponse])


@paper_trading_blueprint.get(
    "/paper-trading", response_model=BotListResponse, tags=["paper trading"]
)
def get(
    status: Status = Status.all,
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    try:
        bots = PaperTradingTableCrud(session=session).get(
            status, start_date, end_date, limit, offset
        )
        data = ta.dump_python(bots)  # type: ignore
        return BotListResponse(
            message="Successfully found paper trading bots!", data=data
        )

    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)
    except ValidationError as error:
        return BotResponse(message="Failed to find bots!", data=error.json(), error=1)


@paper_trading_blueprint.get("/paper-trading/active-pairs", tags=["paper trading"])
def get_active_pairs(session: Session = Depends(get_session)):
    try:
        pairs = PaperTradingTableCrud(session=session).get_active_pairs()
        return BotPairsList(message="Successfully found active pairs!", data=pairs)
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)
    except ValueError as error:
        return BotResponse(message=f"{error}", error=1)


@paper_trading_blueprint.get(
    "/paper-trading/{id}", response_model=BotResponse, tags=["paper trading"]
)
def get_one(
    id: str,
    session: Session = Depends(get_session),
):
    try:
        bot = PaperTradingTableCrud(session=session).get_one(bot_id=id, symbol=None)
        bot_model = BotModelResponse.dump_from_table(bot)
        return BotResponse(
            message="Successfully found one paper trading bot.", data=bot_model
        )
    except ValidationError as error:
        return StandardResponse(message="Bot not found.", error=1, data=error.json())
    except BinbotErrors as error:
        return StandardResponse(message=error.message, error=1)


@paper_trading_blueprint.get(
    "/paper-trading/symbol/{symbol}", response_model=BotResponse, tags=["bots"]
)
def get_one_by_symbol(symbol: str, session: Session = Depends(get_session)):
    try:
        bot = PaperTradingTableCrud(session=session).get_one(bot_id=None, symbol=symbol)
        bot_model = BotModelResponse.dump_from_table(bot)
        return BotResponse(message="Successfully found one bot.", data=bot_model)
    except ValidationError as error:
        return StandardResponse(message="Bot not found.", error=1, data=error.json())
    except BinbotErrors as error:
        return StandardResponse(message=error.message, error=1)


@paper_trading_blueprint.post("/paper-trading", tags=["paper trading"])
def create(bot_item: BotBase, session: Session = Depends(get_session)):
    try:
        bot = PaperTradingTableCrud(session=session).create(bot_item)
        bot_model = BotModel.model_construct(**bot.model_dump())
        return BotResponse(message="Bot created", data=bot_model)
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)


@paper_trading_blueprint.put("/paper-trading/{id}", tags=["paper trading"])
def edit(id: str, bot_item: BotModel, session: Session = Depends(get_session)):
    try:
        controller = PaperTradingTableCrud(session=session)
        bot_table = controller.get_one(id)
        # update model with ne data
        bot_table.sqlmodel_update(bot_item.model_dump())
        # client should not change deal and orders
        # these are internally generated
        transform_model = BotModel.dump_from_table(bot_table)
        bot = controller.save(transform_model)

        bot_model = BotModel.model_construct(**bot.model_dump())
        return BotResponse(message="Bot updated", data=bot_model)
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)


@paper_trading_blueprint.delete("/paper-trading", tags=["paper trading"])
def delete(id: List[str], session: Session = Depends(get_session)):
    """
    Receives a list of `id=a1b2c3&id=b2c3d4`
    """
    try:
        PaperTradingTableCrud(session=session).delete(bot_ids=id)
        return BotResponse(message="Successfully deleted bot!")
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)


@paper_trading_blueprint.get("/paper-trading/activate/{id}", tags=["paper trading"])
def activate(id: str, session: Session = Depends(get_session)):
    bot = PaperTradingTableCrud(session=session).get_one(bot_id=id)
    if not bot:
        return BotResponse(message="Bot not found", error=1)

    bot_model = BotModel.dump_from_table(bot)

    deal_instance = DealGateway(bot=bot_model, db_table=PaperTradingTable)

    try:
        deal_instance.open_deal()
        return BotResponse(message="Successfully activated bot!", data=bot_model)

    except BinbotErrors as error:
        deal_instance.update_logs(message=error.message)
        return BotResponse(data=bot_model, message=error.message, error=1)
    except BinanceErrors as error:
        deal_instance.update_logs(message=error.message)
        return BotResponse(data=bot_model, message=error.message, error=1)


@paper_trading_blueprint.delete(
    "/paper-trading/deactivate/{id}", tags=["paper trading"]
)
def deactivate(id: str, session: Session = Depends(get_session)):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    bot_model = PaperTradingTableCrud(session=session).get_one(bot_id=id)
    if not bot_model:
        return api_response("No active bot found. Can't deactivate")

    bot_model = BotModel.model_construct(**bot_model.model_dump())
    deal_instance = DealGateway(bot=bot_model, db_table=PaperTradingTable)

    try:
        data = deal_instance.deactivation()
        response_data = BotModelResponse(**data.model_dump())
        return {
            "message": "Successfully triggered panic sell! Bot deactivated.",
            "data": response_data,
        }
    except BinbotErrors as error:
        return BotResponse(message=error.message, error=1)
    except ValueError as error:
        return BotResponse(message="Bot not found.", error=1, data=str(error))


@paper_trading_blueprint.post(
    "/paper-trading/errors/{bot_id}", response_model=BotResponse, tags=["bots"]
)
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
        bot_table = PaperTradingTableCrud(session=session).get_one(bot_id=bot_id)
        bot_model = BotModel.dump_from_table(bot_table)
        if not bot_model:
            return BotResponse(message="Bot not found.", error=1)

        data = PaperTradingTableCrud(session=session).update_logs(
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
