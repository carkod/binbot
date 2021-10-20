from bson import json_util
import requests
import json
from decimal import Decimal
import sys
from requests import Response, HTTPError
import sys
class BinanceErrors(Exception):
    pass

class InvalidSymbol(BinanceErrors):
    pass

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


def handle_binance_errors(response: Response, bot=None, message=None):
    """
    Handles:
    - HTTP codes, not authorized, rate limits...
    - Bad request errors, binance internal e.g. {"code": -1013, "msg": "Invalid quantity"}
    - Binbot internal errors - bot errors, returns "errored"

    """
    
    try:
        if isinstance(response, Response) and "X-MBX-USED-WEIGHT-" in response.headers:
            print(f'Current rate limit: {response.headers}')

        if (
            isinstance(json.loads(response.content), dict)
            and "code" in json.loads(response.content).keys()
        ):
            content = response.json()
            if content["code"] == 200:
                return content
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
    except HTTPError:
        raise HTTPError(response.json()["msg"])
