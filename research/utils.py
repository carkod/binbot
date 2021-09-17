import requests
import json
from decimal import Decimal


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

                return print(json.loads(req.content))

    except requests.exceptions.HTTPError as err:
        if err:
            print(req.json())
            return print(req.json())
        else:
            return err
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        return print("handle_error: Timeout")
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        return print("handle_error: Too many Redirects")
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        raise e
