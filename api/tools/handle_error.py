import json
import os
from time import sleep

from bson import json_util
from bson.objectid import ObjectId
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from requests import Response, put
from requests.exceptions import HTTPError

class BinanceErrors(Exception):
    pass


class InvalidSymbol(BinanceErrors):
    pass


class NotEnoughFunds(BinanceErrors):
    pass


class QuantityTooLow(BinanceErrors):
    """
    Raised when LOT_SIZE filter error triggers
    This error should happen in the least cases,
    unless purposedly triggered to check quantity
    e.g. BTC = 0.0001 amounts are usually so small that it's hard to see if it's nothing or a considerable amount compared to others
    """

    pass


def post_error(msg):
    url = f'{os.getenv("FLASK_DOMAIN")}/research/controller'
    res = put(url=url, json={"system_logs": msg})
    handle_binance_errors(res)
    return


def json_response(content, status=200):
    content = json.loads(json_util.dumps(content))
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


def handle_binance_errors(response: Response):
    """
    Handles:
    - HTTP codes, not authorized, rate limits...
    - Bad request errors, binance internal e.g. {"code": -1013, "msg": "Invalid quantity"}
    - Binbot internal errors - bot errors, returns "errored"

    """
    content: dict[str, object] = response.json()

    if response.status_code == 404:
        raise HTTPError()
    # Show error message for bad requests
    if response.status_code >= 400:
        return response.json()

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

    if content and "code" in content:
        if content["code"] == -1013:
            raise QuantityTooLow()
        if content["code"] == 200:
            return content
        if (
            content["code"] == -2010
            or content["code"] == -1013
            or content["code"] == -2015
        ):
            # Not enough funds. Ignore, send to bot errors
            # Need to be dealt with at higher levels
            raise NotEnoughFunds(content["msg"])

        if content["code"] == -1003:
            # Too many requests, most likely exceeded API rate limits
            # Back off for > 5 minutes, which is Binance's ban time
            print("Too many requests. Back off for 1 min...")
            sleep(60)

        if content["code"] == -1121:
            raise InvalidSymbol(f'Binance error: {content["msg"]}')
    else:
        return content


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class StandardResponse(BaseModel):
    message: str
    error: int = 0
