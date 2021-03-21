import requests
import json
from api.tools.jsonresp import jsonResp_message, jsonResp

def handle_error(req):
    try:
        req.raise_for_status()

        if isinstance(json.loads(req.content), dict):
            # Binance code errors
            if 'code' in json.loads(req.content).keys():

                response = req.json()
                if response["code"] == -2010:
                    return jsonResp({"message": "Not enough funds", "error": "true"}, 200)
                
                # Uknown orders ignored, they are used as a trial an error endpoint to close orders (close deals)
                if response["code"] == -2011:
                    return 
                
                return jsonResp_message(json.loads(req.content), 200)

    except requests.exceptions.HTTPError as err:
        if err:
            print(req.json())
            return jsonResp_message(req.json(), 200)
        else:
            return err
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        return jsonResp_message('handle_error: Timeout', 408)
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        return jsonResp_message('handle_error: Too many Redirects', 429)
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        return jsonResp_message(f'Catastrophic error: {e}', 500)
