from fastapi import APIRouter, HTTPException
from tools.round_numbers import format_ts
from charts.models import (
    GetMarketDominationResponse,
    MarketDominationResponse,
    MarketDominationSeries,
)
from tools.handle_error import (
    json_response,
    json_response_error,
    json_response_message,
)
from charts.controllers import Candlestick, MarketDominationController, BtcCorrelation
from charts.models import CandlestickResponse

charts_blueprint = APIRouter()


@charts_blueprint.get(
    "/timeseries",
    summary="Retrieve timeseries data",
    response_model=CandlestickResponse,
    tags=["charts"],
)
def get_timeseries(symbol: str, limit: int = 500):
    """
    Retrieve candlesticks data stored in DB from Binance
    in a timeseries format by Binquant
    """
    data = Candlestick().get_timeseries(symbol, limit)
    return {
        "data": data,
        "message": "Successfully retrieved timeseries data.",
    }


@charts_blueprint.get(
    "/market-domination",
    summary="Market domination (gainers vs losers) data",
    response_model=MarketDominationResponse,
    tags=["charts"],
)
def market_domination(size: int = 14):
    data = MarketDominationController().get_market_domination(size)
    market_domination_series = MarketDominationSeries()

    try:
        for item in data:
            gainers_percent: float = 0
            losers_percent: float = 0
            gainers_count: int = 0
            losers_count: int = 0
            total_volume: float = 0
            if "data" in item:
                for crypto in item["data"]:
                    if float(crypto["priceChangePercent"]) > 0:
                        gainers_percent += float(crypto["volume"])
                        gainers_count += 1

                    if float(crypto["priceChangePercent"]) < 0:
                        losers_percent += abs(float(crypto["volume"]))
                        losers_count += 1

                    if float(crypto["volume"]) > 0:
                        total_volume += float(crypto["volume"]) * float(crypto["price"])

            market_domination_series.dates.append(format_ts(item["time"]))
            market_domination_series.gainers_percent.append(gainers_percent)
            market_domination_series.losers_percent.append(losers_percent)
            market_domination_series.gainers_count.append(gainers_count)
            market_domination_series.losers_count.append(losers_count)
            market_domination_series.total_volume.append(total_volume)

        data = market_domination_series.model_dump(mode="json")

        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved market domination data.",
                "error": 0,
            }
        )
    except Exception as error:
        return json_response_error(
            f"Failed to retrieve market domination data: {error}"
        )


@charts_blueprint.get(
    "/store-market-domination",
    tags=["charts"],
    response_model=GetMarketDominationResponse,
)
def store_market_domination():
    try:
        response = MarketDominationController().store_market_domination()
        if response:
            return json_response_message("Successfully stored market domination data.")
    except Exception as error:
        return json_response_error(f"Failed to store market domination data: {error}")


@charts_blueprint.get("/md-migration", tags=["charts"])
def md_migration():
    try:
        response = MarketDominationController().mkdm_migration()
        if response:
            return json_response_message("Market domination migration completed.")
    except Exception as error:
        return json_response_error(
            f"Failed to migrate market domination data: {error.args[0]}"
        )


@charts_blueprint.get("/top-gainers", tags=["charts"])
def top_gainers():
    try:
        response = MarketDominationController().top_gainers()
        if response:
            return json_response(
                {
                    "data": response,
                    "message": "Successfully retrieved top gainers data.",
                    "error": 0,
                }
            )
        else:
            raise HTTPException(404, detail="No data found")

    except Exception as error:
        return json_response_error(f"Failed to retrieve top gainers data: {error}")


@charts_blueprint.get("/btc-correlation", tags=["charts"])
def get_btc_correlation(symbol: str):
    try:
        response = BtcCorrelation().get_btc_correlation(asset_symbol=symbol)
        if response:
            return json_response(
                {
                    "data": response,
                    "message": "Successfully retrieved BTC correlation data.",
                    "error": 0,
                }
            )
        else:
            raise HTTPException(404, detail="No data found")

    except Exception as error:
        return json_response_error(f"Failed to retrieve BTC correlation data: {error}")


@charts_blueprint.get("/ticker-24", tags=["charts"])
def ticker_24(symbol: str):
    response = Candlestick().ticker_24(symbol=symbol)
    if response:
        return json_response(
            {
                "data": response,
                "message": f"Successfully retrieved 24 hour ticker for {symbol}.",
                "error": 0,
            }
        )
    else:
        raise HTTPException(404, detail="No data found")
