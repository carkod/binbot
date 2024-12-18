from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from tools.enum_definitions import Status
from database.models.paper_trading_table import PaperTradingTable
from database.paper_trading_crud import PaperTradingTableCrud
from database.utils import get_session
from deals.controllers import CreateDealController
from tools.exceptions import BinanceErrors, BinbotErrors
from tools.handle_error import api_response
from bots.models import BotModel
from typing import List


paper_trading_blueprint = APIRouter()


@paper_trading_blueprint.get(
    "/paper-trading", response_model=list[BotModel], tags=["paper trading"]
)
def get(
    status: Status | None = None,
    start_date: float | None = None,
    end_date: float | None = None,
    no_cooldown=False,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    try:
        bot = PaperTradingTableCrud(session=session).get(
            status, start_date, end_date, no_cooldown, limit, offset
        )
        return api_response(detail="Paper trading bots found!", data=bot)

    except BinbotErrors as error:
        return api_response(detail=error.message, error=1)


@paper_trading_blueprint.get("/paper-trading/{id}", tags=["paper trading"])
def get_one(
    id: str,
    session: Session = Depends(get_session),
):
    try:
        bot = PaperTradingTableCrud(session=session).get_one(bot_id=id, symbol=None)
        if not bot:
            return api_response(detail="Bot not found.")
        else:
            return api_response(detail="Bot found", data=bot)
    except ValueError as error:
        return api_response(detail=error.args[0], error=1)


@paper_trading_blueprint.post("/paper-trading", tags=["paper trading"])
def create(bot_item: BotModel, session: Session = Depends(get_session)):
    try:
        bot = PaperTradingTableCrud(session=session).create(bot_item)
        return api_response(detail="Bot created", data=bot)
    except BinbotErrors as error:
        return api_response(detail=error.message, error=1)


@paper_trading_blueprint.put("/paper-trading/{id}", tags=["paper trading"])
def edit(id: str, bot_item: BotModel, session: Session = Depends(get_session)):
    try:
        bot = PaperTradingTableCrud(session=session).save(bot_item)
        return api_response(detail="Bot updated", data=bot)
    except BinbotErrors as error:
        return api_response(detail=error.message, error=1)


@paper_trading_blueprint.delete("/paper-trading", tags=["paper trading"])
def delete(id: List[str] = Query(...), session: Session = Depends(get_session)):
    """
    Receives a list of `id=a1b2c3&id=b2c3d4`
    """
    try:
        PaperTradingTableCrud(session=session).delete(id)
        return api_response(detail="Successfully deleted bot!")
    except BinbotErrors as error:
        return api_response(detail=error.message, error=1)


@paper_trading_blueprint.get("/paper-trading/activate/{id}", tags=["paper trading"])
def activate(id: str, session: Session = Depends(get_session)):
    bot = PaperTradingTableCrud(session=session).get_one(bot_id=id)
    if not bot:
        return api_response("Bot not found.")

    bot_instance = CreateDealController(bot, db_table=PaperTradingTable)

    try:
        bot_instance.open_deal()
        return api_response("Successfully activated bot!")

    except BinbotErrors as error:
        bot_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return api_response(error.message, error=1)
    except BinanceErrors as error:
        bot_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return api_response(error.message, error=1)


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

    bot_instance = CreateDealController(bot_model, PaperTradingTable)
    try:
        bot_instance.close_all()
        return api_response("Active orders closed, sold base asset, deactivated")

    except BinbotErrors as error:
        bot_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return api_response(error.message, error=1)
