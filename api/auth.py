import datetime
import os
from flask import request, current_app
from jose import jwt

from api.tools.handle_error import jsonResp
from flask_httpauth import HTTPTokenAuth
from pymongo.errors import CursorNotFound

auth = HTTPTokenAuth(scheme="Bearer")

@auth.verify_token
def verify_token(token):
    # Local request don't need authentication
    if request.host_url.strip("/") == os.getenv("FLASK_DOMAIN"):
        return True
    try:
        current_app.db.users.find_one(
            {"access_token": token}
        )
        return True
    except CursorNotFound:
        return jsonResp({"message": "Invalid token", "error": 1}, 401)


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
