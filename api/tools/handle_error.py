import json
import sys
from time import time, sleep
import os
from bson.objectid import ObjectId
from flask import Response as FlaskResponse
from requests import Response, put
from requests.exceptions import HTTPError, RequestException, Timeout
from bson import json_util
from api.app import create_app

request_weight = 0
accumulated_time = time()

class BinanceErrors(Exception):
    pass

class InvalidSymbol(BinanceErrors):
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
    except RequestException as e:
        # catastrophic error. bail.
        return jsonResp_message(f"Catastrophic error: {e}", 500)


def handle_binance_errors(response: Response, bot=None, message=None):
    """
    Handles:
    - HTTP codes, not authorized, rate limits...
    - Bad request errors, binance internal e.g. {"code": -1013, "msg": "Invalid quantity"}
    - Binbot internal errors - bot errors, returns "errored"

    """
    # Before doing anything, raise error if response is not 200
    response.raise_for_status()

    # Calculate request weights until blocked by Binance
    if isinstance(response, Response) and "x-mbx-used-weight" in response.headers:
        global request_weight
        request_weight = request_weight + int(response.headers["x-mbx-used-weight"])
        # if (1200 - request_weight) < 0:
        #     sleep(30)
        #     print("Request weight exceeded, waiting 30 secs")

        print(f'{1200 - request_weight} request weight left to be blocked')
        global accumulated_time
        if (time() - accumulated_time) > 60:
            accumulated_time = 0
            request_weight = 0

    if (
        isinstance(json.loads(response.content), dict)
        and "code" in json.loads(response.content).keys()
    ):
        content = response.json()
        if content["code"] == 200:
            return response.json()
        if content["code"] == -2010 or content["code"] == -1013:
            # Not enough funds. Ignore, send to bot errors
            # Need to be dealt with at higher levels
            if not bot:
                return jsonResp_error_message(content["msg"])
            else:
                error = f'{message + content["msg"] if message else content["msg"]}'
                bot["errors"].append(error)
                app = create_app()
                bot = app.db.bots.find_one_and_update(
                    {"_id": ObjectId(bot["_id"])},
                    {"$set": {"status": "error", "errors": bot["errors"]}},
                )
                return "errored"

        if content["code"] == -1003:
            # Too many requests, most likely exceeded API rate limits
            # Back off for > 5 minutes, which is Binance's ban time
            print("Too many requests. Back off for 5 min...")
            sys.exit()
            return

        if content["code"] == -1121:
            raise InvalidSymbol("Binance error, invalid symbol")
    else:
        return response.json()
