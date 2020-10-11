from flask import current_app as app
from flask import request
from functools import wraps
from main.tools.jsonresp import jsonResp
from jose import jwt
import datetime
import os

# Auth Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token = request.headers.get("AccessToken")

        try:
            data = jwt.decode(access_token, os.environ["SECRET_KEY"])
        except Exception as e:
            return JsonResp({"message": "Token is invalid", "exception": str(e)}, 401)

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


def refreshAccessToken(refresh_token):

    # If the refresh_token is still valid, create a new access_token and return it
    try:
        user = app.db.users.find_one(
            {"refresh_token": refresh_token}, {"_id": 0, "id": 1, "email": 1, "plan": 1}
        )

        if user:
            decoded = jwt.decode(refresh_token, os.environ["SECRET_KEY"])
            new_access_token = encodeAccessToken(decoded["user_id"], decoded["email"])
            result = jwt.decode(new_access_token, os.environ["SECRET_KEY"])
            result["new_access_token"] = new_access_token
            resp = JsonResp(result, 200)
        else:
            result = {"message": "Auth refresh token has expired"}
            resp = JsonResp(result, 403)

    except:
        result = {"message": "Auth refresh token has expired"}
        resp = JsonResp(result, 403)

    return resp