from flask import Response
from bson import json_util
import json


def jsonResp(data, status):
    return Response(
        json.dumps(data, default=json_util.default),
        mimetype="application/json",
        status=status,
    )


def jsonResp_message(message, status):
    message = {"message": message}
    return jsonResp(message, status)
