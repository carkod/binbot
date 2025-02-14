import json
import os
import logging
from time import sleep
from typing import Any, Union, TypeVar, Optional
from bson import json_util
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from requests import Response, put
from requests.exceptions import HTTPError
from fastapi.encoders import jsonable_encoder
from copy import deepcopy
from tools.exceptions import (
    BinanceErrors,
    BinbotErrors,
    InvalidSymbol,
    NotEnoughFunds,
    QuantityTooLow,
)


def post_error(msg):
    url = f'{os.getenv("FLASK_DOMAIN")}/research/controller'
    res = put(url=url, json={"system_logs": msg})
    handle_binance_errors(res)
    return


def api_response(detail: str, data: Any = None, error: Union[str, int] = 0, status=200):
    """
    Custom Fast API response

    Args:
    - detail: the message of the response
    - data: Pydantic model returned
    """
    body = {"message": detail}
    if data:
        body["data"] = data

    if error:
        body["error"] = str(error)

    return JSONResponse(
        status_code=status,
        content=body,
    )


def json_response(content, status=200):
    content = json.loads(json_util.dumps(content))  # Objectid serialization
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
    return json_response(body, status=422)


def handle_binance_errors(response: Response) -> dict:
    """
    Handles:
    - HTTP codes, not authorized, rate limits...
    - Bad request errors, binance internal e.g. {"code": -1013, "msg": "Invalid quantity"}
    - Binbot internal errors - bot errors, returns "errored"

    """

    if "x-mbx-used-weight-1m" in response.headers:
        logging.info(
            f"Request to {response.url} weight: {response.headers.get('x-mbx-used-weight-1m')}"
        )
    # Binance doesn't seem to reach 418 or 429 even after 2000 weight requests
    if (
        response.headers.get("x-mbx-used-weight-1m")
        and float(response.headers.get("x-mbx-used-weight-1m", 0)) > 4000
    ):
        logging.warning("Request weight limit prevention pause, waiting 1 min")
        sleep(120)

    if response.status_code == 418 or response.status_code == 429:
        logging.warning("Request weight limit hit, ban will come soon, waiting 1 hour")
        sleep(3600)

    # Cloudfront 403 error
    if response.status_code == 403 and response.reason:
        raise HTTPError(response=response)

    content = response.json()

    if response.status_code == 404:
        raise HTTPError(response=response)

    # Show error messsage for bad requests
    if response.status_code >= 400:
        # Binance errors
        if "msg" in content and "code" in content:
            raise BinanceErrors(content["msg"], content["code"])

        # Binbot errors
        if content and "error" in content and content["error"] == 1:
            raise BinbotErrors(content["message"], content["error"])

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
            raise InvalidSymbol(f'Binance error: {content["msg"]}', content["code"])

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
        content["_id"] = id
    else:
        content = jsonable_encoder(raw)
    return content


class StandardResponse(BaseModel):
    message: str
    error: int = Field(default=0)


DataType = TypeVar("DataType")


class IResponseBase(BaseModel):
    message: str
    error: Optional[int] = Field(default=0)
