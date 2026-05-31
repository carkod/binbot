import logging
from contextlib import asynccontextmanager

from account.routes import account_blueprint
from asset_index.routes import asset_index_blueprint
from autotrade.routes import autotrade_settings_blueprint
from bots.routes import bot_blueprint
from charts.routes import charts_blueprint
from databases.api_db import ApiDb
from databases.tables import *  # noqa
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from grid_ladders.routes import grid_ladder_blueprint
from inquiries.routes import inquiries_router
from orders.routes.binance import binance_order_blueprint
from orders.routes.kucoin import kucoin_order_blueprint
from paper_trading.routes import paper_trading_blueprint
from portfolio.routes import portfolio_blueprint
from pybinbot import configure_logging
from signals.routes import signals_blueprint
from symbols.routes import symbols_blueprint
from user.routes import user_blueprint

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        api_db = ApiDb()
        api_db.init_db()
        pass
    except Exception as error:
        logging.error(f"Error initializing database: {error}")
        pass
    yield


app = FastAPI(title="Binbot API", version="2.0.0", lifespan=lifespan)

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Check app works. Can be used for healthchecks
    """
    return {"message": "online"}


app.include_router(user_blueprint)
app.include_router(account_blueprint, prefix="/account")
app.include_router(bot_blueprint)
app.include_router(paper_trading_blueprint)
app.include_router(binance_order_blueprint, prefix="/order")
app.include_router(kucoin_order_blueprint, prefix="/order/kucoin")
app.include_router(charts_blueprint, prefix="/charts")
app.include_router(symbols_blueprint)
app.include_router(autotrade_settings_blueprint, prefix="/autotrade-settings")
app.include_router(asset_index_blueprint, prefix="/asset-index")
app.include_router(inquiries_router)
app.include_router(portfolio_blueprint)
app.include_router(signals_blueprint)
app.include_router(grid_ladder_blueprint)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {"message": exc.errors(), "data": exc.body, "error": 1}
        ),
    )
