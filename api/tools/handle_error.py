import json
from time import sleep
import os
from bson.objectid import ObjectId
from flask import Response as FlaskResponse
from pymongo import ReturnDocument
from requests import Response, put
from requests.exceptions import HTTPError, Timeout
from bson import json_util
from api.app import create_app


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


def jsonResp(data, status=200):
    return FlaskResponse(
        json.dumps(data, default=json_util.default),
        mimetype="application/json",
        status=status,
    )


def jsonResp_message(message):
    message = {"message": message, "error": 0}
    return jsonResp(message)


def jsonResp_error_message(message):
    body = {"message": message, "error": 1}
    return jsonResp(body)


def bot_errors(error, bot, status="error"):
    """
    params status refer to bot-status.md
    """
    if isinstance(error, Response):
        try:
            error = error.json()["msg"]
        except KeyError:
            error = error.json()["message"]
    else:
        error = error

    bot["errors"].append(error)
    app = create_app()
    bot = app.db.bots.find_one_and_update(
        {"_id": ObjectId(bot["_id"])},
        {"$set": {"status": status, "errors": bot["errors"]}},
        return_document=ReturnDocument.AFTER
    )

    return bot


def handle_error(req):
    try:
        req.raise_for_status()

        if isinstance(json.loads(req.content), dict):
            # Binance code errors
            if "code" in json.loads(req.content).keys():

                response = req.json()
                if response["code"] == -2010:
                    return jsonResp({"message": "Not enough funds", "error": 1}, 200)

                # Uknown orders ignored, they are used as a trial an error endpoint to close orders (close deals)
                if response["code"] == -2011:
                    return

                return jsonResp_message(json.loads(req.content))

    except HTTPError as err:
        if err:
            print(req.json())
            return jsonResp_message(req.json())
        else:
            return err
    except Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        return jsonResp_message("handle_error: Timeout", 408)


def handle_binance_errors(response: Response, bot=None, message=None):
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
        if content["code"] == -2010 or content["code"] == -1013 or content["code"] == -2015:
            # Not enough funds. Ignore, send to bot errors
            # Need to be dealt with at higher levels
            raise NotEnoughFunds(content["msg"])

        if content["code"] == -1003:
            # Too many requests, most likely exceeded API rate limits
            # Back off for > 5 minutes, which is Binance's ban time
            print("Too many requests. Back off for 1 min...")
            sleep(60)

        if content["code"] == -1121:
            raise InvalidSymbol("Binance error, invalid symbol")
    else:
        return content
