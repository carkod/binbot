import datetime
import os

from flask import current_app, request
from flask_httpauth import HTTPTokenAuth
from jose import jwt

auth = HTTPTokenAuth(scheme="Bearer")


# @auth.verify_token
# def verify_token(token):
#     # Research app exception
#     # Authorize local requests
#     print("Flask request headers", request.headers.environ)
#     if request.headers.environ["REMOTE_ADDR"] == "127.0.0.1":
#         return True
#     user = current_app.db.users.find_one({"access_token": token})
#     if user:
#         return True
#     else:
#         return False


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
