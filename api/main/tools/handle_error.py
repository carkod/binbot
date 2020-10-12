import requests
import json
from main.tools.jsonresp import jsonResp_message

def handle_error(req):
    try:
        req.raise_for_status()
        # Binance code errors
        if 'code' in json.loads(req.content).keys():
            return jsonResp_message(json.loads(req.content), 200)

    except requests.exceptions.HTTPError as err:
        if err:
            print(req.json())
            return jsonResp_message(req.json(), 200)
        else:
            return err
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        return jsonResp_message('handle_error: Timeout', 200)
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        return jsonResp_message('handle_error: Too many Redirects', 200)
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        return jsonResp_message(f'Catastrophic error: {e}', 200)
