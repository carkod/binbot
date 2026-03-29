from time import time
from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import Optional
from pybinbot import Status, BinbotErrors, BinanceErrors
from user.models.user import UserTokenData
from bots.models import (
    BotBase,
    BotResponse,
    BotListResponse,
    BulkDeleteRequest,
    BotModel,
    ErrorsRequestBody,
)
from databases.crud.bot_crud import BotTableCrud
from databases.utils import get_session
from deals.gateway import DealGateway
from databases.tables.bot_table import BotTable, PaperTradingTable
from exchange_apis.kucoin.futures.position_deal import PositionDeal
from kucoin_universal_sdk.model.common import RestError
from user.services.auth import get_current_user

bot_blueprint = APIRouter()


@bot_blueprint.get("/bot", response_model=BotListResponse, tags=["bots"])
def get_bots(
    status: Status = Status.all,
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    try:
        bots = crud.get(
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        data = [BotModel.dump_from_table(bot) for bot in bots]
        return BotListResponse(message="Successfully found bots!", data=data)
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.get("/bot/active-pairs", response_model=BotListResponse, tags=["bots"])
def get_active_pairs(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    try:
        pairs = crud.get_active_pairs()
        return BotListResponse(message="Successfully found active pairs.", data=pairs)
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.get("/bot/public", response_model=BotListResponse, tags=["bots"])
def get_public_bots(
    status: Status = Status.all,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """
    Public endpoint replica of get_bots
    No auth required
    """
    crud = BotTableCrud(session)
    end_date = time() * 1000
    start_date = end_date - 7 * 24 * 60 * 60 * 1000
    try:
        bots = crud.get(
            status=status,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )
        bot_profit_list = []
        for bot in bots:
            opening = bot.deal.opening_price
            closing = (
                bot.deal.closing_price
                if bot.deal.closing_price
                else bot.deal.current_price
            )
            if opening and opening != 0:
                profit_pct = (closing - opening) / opening
            else:
                continue

            bot_profit_list.append((bot, profit_pct))

        # Sort by profit percentage descending and take top 4
        top_bots = [
            bp[0]
            for bp in sorted(bot_profit_list, key=lambda x: x[1], reverse=True)[:4]
        ]

        data = []
        for bot in top_bots:
            bot_model = BotModel.dump_from_table(bot)
            # Clear confidential data
            bot_model.logs = []
            bot_model.orders = []
            bot_model.id = "redacted"
            data.append(bot_model)

        return BotListResponse(message="Successfully found bots!", data=data)
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.get("/bot/{bot_id}", response_model=BotResponse, tags=["bots"])
def get_one_by_id(
    bot_id: str,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    try:
        bot_row = crud.get_one(bot_id=bot_id)
        bot_model = BotModel.dump_from_table(bot_row)
        return BotResponse(message="Successfully found one bot.", data=bot_model)
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.get("/bot/symbol/{symbol}", response_model=BotResponse, tags=["bots"])
def get_one_by_symbol(
    symbol: str,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    try:
        bot_row = crud.get_one(symbol=symbol)
        bot_model = BotModel.dump_from_table(bot_row)
        return BotResponse(message="Successfully found one bot.", data=bot_model)
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.post("/bot", response_model=BotResponse, tags=["bots"])
def create_bot(
    bot_item: BotBase,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    bot_row = crud.create(bot_item)
    bot_model = BotModel.dump_from_table(bot_row)
    return BotResponse(message="Successfully created one bot.", data=bot_model)


@bot_blueprint.put("/bot/{bot_id}", response_model=BotResponse, tags=["bots"])
def edit_bot(
    bot_id: str,
    bot_item: BotBase,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    bot_row = crud.get_one(bot_id=bot_id)
    bot_row.sqlmodel_update(bot_item.model_dump())
    updated_row = crud.save(bot_row)
    bot_model = BotModel.dump_from_table(updated_row)
    return BotResponse(message="Successfully edited bot.", data=bot_model)


@bot_blueprint.delete("/bot", response_model=BotResponse, tags=["bots"])
def delete_bots(
    payload: BulkDeleteRequest,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    crud.delete(bot_ids=payload.ids)
    return BotResponse(message="Successfully deleted bots.")


@bot_blueprint.get("/bot/activate/{bot_id}", response_model=BotResponse, tags=["bots"])
def activate_bot(
    bot_id: str,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    bot_row = crud.get_one(bot_id=bot_id)
    bot_model = BotModel.dump_from_table(bot_row)
    deal_gateway = DealGateway(bot_model, db_table=BotTable)
    if isinstance(deal_gateway.deal, PositionDeal) and bot_model.margin_short_reversal:
        can_reverse, msg = deal_gateway.deal.estimate_reversal_possible_for_new_bot()
        if not can_reverse:
            bot_model.margin_short_reversal = False
            bot_model.add_log(
                f"{msg} margin_short_reversal has been automatically deactivated due to lack of funds."
            )
            deal_gateway.save(bot_model)
    try:
        activated_bot = deal_gateway.open_deal()
        bot_model = BotModel.dump_from_table(activated_bot)
        message = "Successfully activated bot."
        if bot_row.status == Status.active:
            message = "Successfully updated bot."
        return BotResponse(message=message, data=bot_model)
    except (BinbotErrors, BinanceErrors, RestError) as e:
        deal_gateway.update_logs(str(e))
        bot_model = BotModel.dump_from_table(bot_row)
        return BotResponse(message=str(e), data=bot_model, error=1)


@bot_blueprint.delete(
    "/bot/deactivate/{bot_id}", response_model=BotResponse, tags=["bots"]
)
def deactivate_bot(
    bot_id: str,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    bot_row = crud.get_one(bot_id=bot_id)
    if not isinstance(bot_row, (BotTable, PaperTradingTable)):
        return BotResponse(message="Invalid bot data.", error=1)

    bot_model = BotModel.dump_from_table(bot_row)
    deal_gateway = DealGateway(bot_model, db_table=BotTable)
    try:
        deactivated_bot = deal_gateway.deactivation()
        bot_model = BotModel.dump_from_table(deactivated_bot)
        return BotResponse(
            message="Successfully triggered panic sell! Bot deactivated.",
            data=bot_model,
        )
    except BinbotErrors as e:
        bot_model = BotModel.dump_from_table(bot_row)
        return BotResponse(message=e.message, data=bot_model, error=1)


@bot_blueprint.post("/bot/errors/{bot_id}", response_model=BotResponse, tags=["bots"])
def post_bot_errors(
    bot_id: str,
    bot_errors: ErrorsRequestBody,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    bot_row = crud.get_one(bot_id=bot_id)
    errors_list = bot_errors.errors if hasattr(bot_errors, "errors") else []
    updated_bot = crud.update_logs(errors_list, bot_row)
    bot_model = BotModel.dump_from_table(updated_bot)
    return BotResponse(message="Errors posted successfully.", data=bot_model, error=0)
