from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from portfolio.models import BenchmarkSeriesResponse
from portfolio.controller import PortfolioController
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from sqlmodel import Session
from databases.utils import get_session

portfolio_blueprint = APIRouter(prefix="/portfolio")


@portfolio_blueprint.get(
    "/benchmark-series", response_model=BenchmarkSeriesResponse, tags=["portfolio"]
)
def get_benchmark_series(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    today = datetime.now()
    month_ago = today - timedelta(days=30)
    start_date = int(datetime.timestamp(month_ago) * 1000)
    end_date = int(datetime.timestamp(today) * 1000)
    controller = PortfolioController(session=session)
    data = controller.map_balance_with_benchmark(
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "data": data,
        "message": "Successfully retrieved benchmark series.",
    }
