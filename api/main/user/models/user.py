from flask import request, current_app as app
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import auth
import os
from main.tools.dates import nowDatetimeUTC
from main.tools.jsonresp import jsonResp_message, jsonResp
import json
from bson.objectid import ObjectId

class User:

    def __init__(self):
        self.defaults = {
            "email": "",
            "password": "",
            "username": "",
            "description": "",
            "access_token": "",
            "refresh_token": ""
        }

    def get(self):
        # token_data = jwt.decode(request.headers.get('AccessToken'), os.environ['SECRET_KEY'])
        users = list(app.db.users.find())
        if users:
            resp = jsonResp_message(users, 200)
        else:
            resp = jsonResp_message("No users found", 200)

        return resp

    def get_one(self):
        findId = request.view_args["id"]
        user = app.db.users.find_one({"_id": ObjectId(findId)})

        if user:
            resp = jsonResp({"message": "User found", "data": user}, 200)
        else:
            resp = jsonResp({"message": "User not found"}, 404)
        return resp

    def getAuth(self):
        access_token = request.headers.get("AccessToken")
        refresh_token = request.headers.get("RefreshToken")
        resp = jsonResp_message({"message": "User not logged in"}, 401)

        if access_token:
            try:
                decoded = jwt.decode(access_token, os.environ["SECRET_KEY"])
                resp = jsonResp_message(decoded, 200)
            except:
                # If the access_token has expired, get a new access_token - so long as the refresh_token hasn't expired yet
                resp = auth.refreshAccessToken(refresh_token)

        return resp

    def login(self):
        resp = jsonResp_message("Invalid user credentials", 403)

        try:
            data = json.loads(request.data)
            email = data["email"].lower()
            user = app.db.users.find_one({"email": email})

            if user and pbkdf2_sha256.verify(data["password"], user["password"]):
                access_token = auth.encodeAccessToken(user["id"], user["email"])
                refresh_token = auth.encodeRefreshToken(user["id"], user["email"])

                app.db.users.update({"id": user["id"]}, {"$set": {
                    "refresh_token": refresh_token,
                    "last_login": nowDatetimeUTC()
                }})

                resp = jsonResp({
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

        resp = jsonResp_message("User logged out", 200)

        return resp

    def add(self):
        data = request.json
        expected_data = {
            "email": data['email'].lower(),
            "password": data['password'],
        }
        # Merge the posted data with the default user attributes
        self.defaults.update(expected_data)
        user = self.defaults
        # Encrypt the password
        user["password"] = pbkdf2_sha256.encrypt(user["password"], rounds=20000, salt_size=16)
        # Make sure there isn"t already a user with this email address
        existing_email = app.db.users.find_one({"email": user["email"]})

        if existing_email:
            resp = jsonResp_message({
                "message": "There's already an account with this email address",
            }, 200)

        else:
            insertion = app.db.users.insert(user)
            if insertion:

                # Log the user in (create and return tokens)
                access_token = auth.encodeAccessToken(user["password"], user["email"])
                refresh_token = auth.encodeRefreshToken(user["password"], user["email"])

                app.db.users.update_one({"_id": user["_id"]}, {
                    "$set": {
                        "refresh_token": refresh_token
                    }
                })

                resp = jsonResp_message({
                    "_id": user["_id"],
                    "email": user["email"],
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }, 200)

            else:
                resp = jsonResp_message("User could not be added", 200)
        return resp

    def delete(self):
        findId = request.view_args["id"]
        count = app.db.users.delete_one({"_id": ObjectId(findId)}).deleted_count
        if count > 0:
            resp = jsonResp(
                {"message": "Successfully deleted user"}, 200
            )
        else:
            resp = jsonResp({"message": "Not found user, cannot delete"}, 200)
        return resp
