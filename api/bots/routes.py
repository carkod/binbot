import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from time import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session
from pybinbot import BotBase, Status, BinbotErrors, BinanceErrors, MarketType
from api.user.models.user import UserTokenData
from pybinbot import (
    BotResponse,
    BotListResponse,
    BotPairsList,
    BulkDeleteRequest,
    BotModel,
    ErrorsRequestBody,
)
from api.databases.crud.bot_crud import BotTableCrud
from api.databases.crud.grid_ladder_crud import GridLadderCrud
from api.databases.utils import get_session
from api.deals.gateway import DealGateway
from api.databases.tables.bot_table import BotTable
from api.exchange_apis.kucoin.futures.futures_deal import (
    EntryLiquidityError,
)
from kucoin_universal_sdk.model.common import RestError
from api.user.services.auth import get_current_user
from uuid import UUID

bot_blueprint = APIRouter()
logger = logging.getLogger(__name__)


async def stream_bot_operation(
    operation: Callable[[Callable[[int, str], None]], BotResponse],
) -> AsyncIterator[str]:
    """Run the trade once while sending progress on the same POST response."""
    loop = asyncio.get_running_loop()
    updates: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    def report(percent: int, message: str) -> None:
        loop.call_soon_threadsafe(
            updates.put_nowait,
            ("progress", {"percent": percent, "message": message}),
        )

    def run() -> None:
        try:
            result = operation(report)
            loop.call_soon_threadsafe(
                updates.put_nowait,
                ("result", {"percent": 100, "response": jsonable_encoder(result)}),
            )
        except Exception:
            logger.exception("Bot operation failed after streaming started")
            loop.call_soon_threadsafe(
                updates.put_nowait,
                (
                    "error",
                    {
                        "message": "Bot operation failed; refresh the bot before retrying."
                    },
                ),
            )

    # An exchange call must finish even if the browser closes the stream.
    loop.run_in_executor(None, run)
    while True:
        try:
            event, data = await asyncio.wait_for(updates.get(), timeout=15)
        except TimeoutError:
            yield ": keepalive\n\n"
            continue
        yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
        if event in {"result", "error"}:
            return


@bot_blueprint.get("/bot", response_model=BotListResponse, tags=["bots"])
def get_bots(
    status: Status = Status.all,
    start_date: int | None = None,
    end_date: int | None = None,
    limit: int = 200,
    offset: int = 0,
    bot_name: str | None = None,
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
            bot_name=bot_name,
        )
        data = [BotModel.dump_from_table(bot) for bot in bots]
        return BotListResponse(message="Successfully found bots!", data=data)
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.get("/bot/active-pairs", response_model=BotPairsList, tags=["bots"])
def get_active_pairs(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    try:
        pairs = crud.get_active_pairs()
        return BotPairsList(
            message="Successfully found active pairs.", data=list(pairs)
        )
    except BinbotErrors as e:
        return BotResponse(message=e.message, error=1)


@bot_blueprint.get("/bot/algo-ranking", tags=["bots"])
def get_algo_ranking(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    try:
        ranking = crud.get_list_algo()
        return JSONResponse(content={"detail": jsonable_encoder(ranking)})
    except BinbotErrors as e:
        raise HTTPException(status_code=400, detail=e.message)


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
            bot_model.id = UUID(int=0)
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
    grid_ladder_crud = GridLadderCrud(session)
    active_ladder = grid_ladder_crud.get_active_for_symbol(bot_item.pair)
    if active_ladder is not None and MarketType(
        active_ladder.market_type
    ) == MarketType(bot_item.market_type):
        grid_ladder_crud.update_logs(
            active_ladder.id,
            (
                f"Rejected bot create for {bot_item.pair} ({bot_item.name}): "
                "active grid ladder already owns symbol."
            ),
        )
        raise HTTPException(
            status_code=400,
            detail="An active grid ladder already exists for this symbol",
        )

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
    if (
        bot_item.recovery_params is not None
        and bot_row.deal.position_size_order is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="Recovery cannot be enabled while a position sizing order is unsettled",
        )
    excluded_fields = {"recovery_params"}
    if "futures_leverage" not in bot_item.model_fields_set:
        excluded_fields.add("futures_leverage")
    bot_row.sqlmodel_update(bot_item.model_dump(exclude=excluded_fields))
    updated_row = crud.save(
        bot_row,
        recovery_params_submitted="recovery_params" in bot_item.model_fields_set,
        recovery_params=bot_item.recovery_params,
    )
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


@bot_blueprint.post("/bot/activate/{bot_id}", response_model=BotResponse, tags=["bots"])
def activate_bot(
    bot_id: str,
    request: Request,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    crud = BotTableCrud(session)
    bot_row = crud.get_one(bot_id=bot_id)
    bot_model = BotModel.dump_from_table(bot_row)
    deal_gateway = DealGateway(bot_model, db_table=BotTable)

    def run(progress: Callable[[int, str], None] | None = None) -> BotResponse:
        if progress:
            progress(20, "Bot loaded; preparing activation")
        try:
            activated_bot = deal_gateway.open_deal(progress=progress)
            message = "Successfully activated bot."
            if activated_bot.status == Status.pending:
                message = "Entry order submitted; bot pending exchange fill."
            elif bot_row.status == Status.active:
                message = "Successfully updated bot."
            return BotResponse(message=message, data=activated_bot)
        except EntryLiquidityError as e:
            updated_bot = BotModel.dump_from_table(
                BotTableCrud().get_one(bot_id=bot_id)
            )
            return BotResponse(message=str(e), data=updated_bot, error=1)
        except (BinbotErrors, BinanceErrors, RestError) as e:
            deal_gateway.update_logs(str(e))
            return BotResponse(message=str(e), data=bot_model, error=1)

    if "text/event-stream" in request.headers.get("accept", ""):
        return StreamingResponse(
            stream_bot_operation(run),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return run()


@bot_blueprint.post(
    "/bot/deactivate/{bot_id}", response_model=BotResponse, tags=["bots"]
)
def deactivate_bot(
    bot_id: str,
    request: Request,
    algorithmic_close: bool = False,
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    """
    Deactivation means closing all deals and selling to fiat (USDT at the time of writing)
    to realize profits or losses.

    This could be done for several reasons:
        - Panic close. We need to cut loses, this is the drastic measure that will stop everything and deposses the asset
        - Algorithmic close. A Binquant strategy has decided to close due to market conditions or rules
    """
    crud = BotTableCrud(session)
    bot_row = crud.get_one(bot_id=bot_id)
    if not isinstance(bot_row, BotTable):
        return BotResponse(message="Invalid bot data.", error=1)

    bot_model = BotModel.dump_from_table(bot_row)
    deal_gateway = DealGateway(bot_model, db_table=BotTable)

    def run(progress: Callable[[int, str], None] | None = None) -> BotResponse:
        if progress:
            progress(20, "Bot loaded; preparing close")
        try:
            deactivated_bot = deal_gateway.deactivation(
                algorithmic_close=algorithmic_close, progress=progress
            )
            return BotResponse(
                message="Successfully triggered panic sell! Bot deactivated.",
                data=deactivated_bot,
            )
        except BinbotErrors as e:
            return BotResponse(message=e.message, data=bot_model, error=1)

    if "text/event-stream" in request.headers.get("accept", ""):
        return StreamingResponse(
            stream_bot_operation(run),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return run()


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
