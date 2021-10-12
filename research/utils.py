import requests
import json
from decimal import Decimal
import sys
from requests import Response

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


def supress_notation(num: float, precision: int = 0):
    """
    Supress scientific notation
    e.g. 8e-5 = "0.00008"
    """
    num = float(num)
    if precision >= 0:
        decimal_points = precision
    else:
        decimal_points = Decimal(str(num)).as_tuple().exponent * -1
    return f"{num:.{decimal_points}f}"


def handle_binance_errors(response: Response, bot=None, **kwargs):
    """
    Combine Binance errors
    e.g. {"code": -1013, "msg": "Invalid quantity"}
    and bot errors
    returns "errored" or ""
    """
    if isinstance(json.loads(response.content), dict) and "code" in json.loads(response.content).keys():
        content = response.json()
        if content["code"] == -2010 or content["code"] == -1013:
            # Not enough funds. Ignore, send to bot errors
            # Need to be dealt with at higher levels
            if not bot:
                return jsonResp_error_message(content["msg"])
            else:
                return "errored"

        if content["code"] == -1003:
            # Too many requests, most likely exceeded API rate limits
            # Back off for > 5 minutes, which is Binance's ban time
            print('Too many requests. Back off...')
            sys.exit()
            return
    else:
        return response.json()
