from flask import current_app as app
from flask import Flask, request
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools
from main import auth
import json

class User:

    def __init__(self):
        self.defaults = {

            "email": "",
        }

    def get(self):
        token_data = jwt.decode(request.headers.get('AccessToken'), os.environ['SECRET_KEY'])

        user = app.db.users.find_one({"id": token_data['userid']}, {
            "id": 0,
            "password": 0
        })

        if user:
            resp = json.jsonResp(user, 200)
        else:
            resp = json.jsonResp({"message": "User not found"}, 404)

        return resp

    def getAuth(self):
        access_token = request.headers.get("AccessToken")
        refresh_token = request.headers.get("RefreshToken")

        resp = json.jsonResp({"message": "User not logged in"}, 401)

        if access_token:
            try:
                decoded = jwt.decode(access_token, os.environ["SECRET_KEY"])
                resp = json.jsonResp(decoded, 200)
            except:
                # If the access_token has expired, get a new access_token - so long as the refresh_token hasn't expired yet
                resp = auth.refreshAccessToken(refresh_token)

        return resp

    def login(self):
        resp = json.jsonResp({"message": "Invalid user credentials"}, 403)

        try:
            data = json.loads(request.data)
            email = data["email"].lower()
            user = app.db.users.find_one({"email": email})

            if user and pbkdf2_sha256.verify(data["password"], user["password"]):
                access_token = auth.encodeAccessToken(user["id"], user["email"])
                refresh_token = auth.encodeRefreshToken(user["id"], user["email"])

                app.db.users.update({"id": user["id"]}, {"$set": {
                    "refresh_token": refresh_token,
                    "last_login": tools.nowDatetimeUTC()
                }})

                resp = json.jsonResp({
                    "id": user["id"],
                    "email": user["email"],
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }, 200)

        except Exception:
            pass

        return resp

    def logout(self):
        try:
            tokenData = jwt.decode(request.headers.get("AccessToken"), os.environ["SECRET_KEY"])
            app.db.users.update({"id": tokenData["userid"]}, {'$unset': {"refresh_token": ""}})
            # Note: At some point I need to implement Token Revoking/Blacklisting
            # General info here: https://flask-jwt-extended.readthedocs.io/en/latest/blacklist_and_token_revoking.html
        except:
            pass

        resp = json.jsonResp({"message": "User logged out"}, 200)

        return resp

    def add(self):
        data = json.loads(request.data)
        expected_data = {
            "username": data['username'],
            "email": data['email'].lower(),
            "password": data['password'],
            "description": data['password']
        }

        # Merge the posted data with the default user attributes
        self.defaults.update(expected_data)
        user = self.defaults

        # Encrypt the password
        user["password"] = pbkdf2_sha256.encrypt(user["password"], rounds=20000, salt_size=16)

        # Make sure there isn"t already a user with this email address
        existing_email = app.db.users.find_one({"email": user["email"]})

        if existing_email:
            resp = json.jsonResp({
                "message": "There's already an account with this email address",
                "error": "email_exists"
            }, 400)

        else:
            if app.db.users.save(user):

                # Log the user in (create and return tokens)
                access_token = auth.encodeAccessToken(user["id"], user["email"])
                refresh_token = auth.encodeRefreshToken(user["id"], user["email"])

                app.db.users.update({"id": user["id"]}, {
                    "$set": {
                        "refresh_token": refresh_token
                    }
                })

                resp = json.jsonResp({
                    "id": user["id"],
                    "email": user["email"],
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }, 200)

            else:
                resp = json.jsonResp({"message": "User could not be added"}, 400)

        return resp
