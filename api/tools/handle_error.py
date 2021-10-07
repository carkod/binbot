import json
from time import sleep

from bson.objectid import ObjectId
from flask import current_app, Response as FlaskResponse
from requests import exceptions, Response
from requests.exceptions import HTTPError, RequestException, Timeout
from bson import json_util


def jsonResp(data, status=200):
    return FlaskResponse(
        json.dumps(data, default=json_util.default),
        mimetype="application/json",
        status=status,
    )

def jsonResp_message(message, status):
    message = {"message": message, "error": 0}
    return jsonResp(message, status)

def jsonResp_error_message(message, status):
    body = {"message": message, "error": 1}
    return jsonResp(body, status)
    

def bot_errors(error, bot):
    if isinstance(error, Response):
        try:
            error = error.json()["msg"]
        except KeyError:
            error = error.json()["message"]
    else:
        error = error

    bot["errors"].append(error)
    bot = current_app.db.bots.find_one_and_update(
        {"_id": ObjectId(bot["_id"])},
        {
            "$set": {"status": "error", "errors": bot["errors"]}
        }
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
                    return jsonResp(
                        {"message": "Not enough funds", "error": 1}, 200
                    )

                # Uknown orders ignored, they are used as a trial an error endpoint to close orders (close deals)
                if response["code"] == -2011:
                    return

                return jsonResp_message(json.loads(req.content), 200)

    except HTTPError as err:
        if err:
            print(req.json())
            return jsonResp_message(req.json(), 200)
        else:
            return err
    except Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        return jsonResp_message("handle_error: Timeout", 408)
    except RequestException as e:
        # catastrophic error. bail.
        return jsonResp_message(f"Catastrophic error: {e}", 500)


def handle_binance_errors(response):
    """
    Better handling of errors Binance errors
    e.g. {"code": -1013, "msg": "Invalid quantity"}
    """
    if isinstance(json.loads(response.content), dict) and "code" in json.loads(response.content).keys():
        content = response.json()
        if content["code"] == -2010 or content["code"] == -1013:
            # Not enough funds. Ignore, send to bot errors
            # Need to be dealt with at higher levels
            return jsonResp_error_message(content["msg"])

        if content["code"] == -1003:
            # Too many requests, most likely exceeded API rate limits
            # Back off for > 5 minutes, which is Binance's ban time
            sleep(35)
            return
