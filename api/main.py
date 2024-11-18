from pymongo.errors import ServerSelectionTimeoutError
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from account.routes import account_blueprint
from autotrade.routes import autotrade_settings_blueprint
from bots.routes import bot_blueprint
from charts.routes import charts_blueprint
from orders.routes import order_blueprint
from paper_trading.routes import paper_trading_blueprint
from research.routes import research_blueprint
from user.routes import user_blueprint

from database.api_db import ApiDb
from database.models import *  # noqa


# Startup operations
# needed to be run before app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        api_db = ApiDb()
        api_db.init_db()
        api_db.create_dummy_bot()
        result = api_db.select_bot("BTCUSDT")
        print("Added dummy bot: ", result)
    except ServerSelectionTimeoutError:
        pass
    except Exception as e:
        print("Error", e)

    finally:
        yield


app = FastAPI(lifespan=lifespan)

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Fix issue with curl returning method not allowed (https://github.com/tiangolo/fastapi/issues/1773)
@app.head("/")
# Routes
@app.get("/")
def root():
    """
    Check app works
    """
    return {"status": "Online"}


app.include_router(user_blueprint)
app.include_router(account_blueprint, prefix="/account")
app.include_router(bot_blueprint)
app.include_router(paper_trading_blueprint)
app.include_router(order_blueprint, prefix="/order")
app.include_router(charts_blueprint, prefix="/charts")
app.include_router(research_blueprint, prefix="/research")
app.include_router(autotrade_settings_blueprint, prefix="/autotrade-settings")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {"message": exc.errors(), "data": exc.body, "error": 1}
        ),
    )
