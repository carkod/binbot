import datetime
import os
from functools import wraps

from api.tools.handle_error import jsonResp
from flask import request
from jose import jwt


# Auth Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token = request.headers.get("AccessToken")

        try:
            data = jwt.decode(access_token, os.environ["SECRET_KEY"])
        except Exception as e:
            return jsonResp({"message": "Token is invalid", "exception": str(e)}, 401)

        return f(*args, **kwargs)

    return decorated


def encodeAccessToken(user_id, email):

    accessToken = jwt.encode(
        {
            "user_id": user_id,
            "email": email,
            "exp": datetime.datetime.utcnow()
            + datetime.timedelta(minutes=15),  # The token will expire in 15 minutes
        },
        os.environ["SECRET_KEY"],
        algorithm="HS256",
    )

    return accessToken


def encodeRefreshToken(user_id, email):

    refreshToken = jwt.encode(
        {
            "user_id": user_id,
            "email": email,
            "exp": datetime.datetime.utcnow()
            + datetime.timedelta(weeks=4),  # The token will expire in 4 weeks
        },
        os.environ["SECRET_KEY"],
        algorithm="HS256",
    )

    return refreshToken
