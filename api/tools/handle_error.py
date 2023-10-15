import json
import os
from time import sleep

from bson import json_util
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from requests import Response, put
from requests.exceptions import HTTPError
from fastapi.encoders import jsonable_encoder
from copy import deepcopy
from tools.exceptions import BinanceErrors, BinbotErrors, InvalidSymbol, NotEnoughFunds, QuantityTooLow



def post_error(msg):
    url = f'{os.getenv("FLASK_DOMAIN")}/research/controller'
    res = put(url=url, json={"system_logs": msg})
    handle_binance_errors(res)
    return


def json_response(content, status=200):
    content = json.loads(json_util.dumps(content)) # Objectid serialization
    response = JSONResponse(
        status_code=status,
        content=content,
        media_type="application/json",
    )
    return response


def json_response_message(message):
    body = {"message": message, "error": 0}
    return json_response(body)


def json_response_error(message):
    body = {"message": message, "error": 1}
    return json_response(body)


def handle_binance_errors(response: Response) -> str | None:
    """
    Handles:
    - HTTP codes, not authorized, rate limits...
    - Bad request errors, binance internal e.g. {"code": -1013, "msg": "Invalid quantity"}
    - Binbot internal errors - bot errors, returns "errored"

    """
    content = response.json()

    if response.status_code == 404:
        raise HTTPError()
    # Show error message for bad requests
    if response.status_code >= 400:
        error = response.json()
        if "msg" in error:
            raise BinanceErrors(error["msg"], error["code"])
        if "error" in error:
            raise BinbotErrors(error["message"])

    if response.status_code == 418 or response.status_code == 429:
        print("Request weight limit hit, ban will come soon, waiting 1 hour")
        sleep(3600)

    # Calculate request weights and pause half of the way (1200/2=600)
    if (
        "x-mbx-used-weight-1m" in response.headers
        and int(response.headers["x-mbx-used-weight-1m"]) > 600
    ):
        print("Request weight limit prevention pause, waiting 1 min")
        sleep(120)

    # Binbot errors
    if content and "error" in content and content["error"] == 1:
        raise BinanceErrors(content["message"], content["error"])

    # Binance errors
    if content and "code" in content:
        if content["code"] == -1013:
            raise QuantityTooLow(content["message"], content["error"])
        if content["code"] == 200:
            return content
        if (
            content["code"] == -2010
            or content["code"] == -1013
            or content["code"] == -2015
        ):
            # Not enough funds. Ignore, send to bot errors
            # Need to be dealt with at higher levels
            raise NotEnoughFunds(content["msg"], content["code"])

        if content["code"] == -1003:
            # Too many requests, most likely exceeded API rate limits
            # Back off for > 5 minutes, which is Binance's ban time
            print("Too many requests. Back off for 1 min...")
            sleep(60)

        if content["code"] == -1121:
            raise InvalidSymbol(f'Binance error: {content["msg"]}', content["msg"])
    
    return content


def encode_json(raw):
    """
    Wrapper for jsonable_encoder to encode ObjectId
    """
    if hasattr(raw, "_id"):
        # Objectid serialization
        id = str(raw._id)
        content = deepcopy(raw)
        del content._id
        content = jsonable_encoder(content)
        content["_id"]= id
    else:
        content = jsonable_encoder(raw) 
    return content


class StandardResponse(BaseModel):
    message: str
    error: int = 0
