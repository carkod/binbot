from flask import request, current_app as app
from passlib.hash import pbkdf2_sha256
from jose import jwt
from api.auth import encodeAccessToken, encodeRefreshToken
import os
from api.tools.dates import nowDatetimeUTC
from api.tools.jsonresp import jsonResp_message, jsonResp
from bson.objectid import ObjectId

class User:

    def __init__(self):
        self.defaults = {
            "email": "",
            "password": "",
            "username": "",
            "description": "",
            "access_token": "",
            "last_login": "",
            "created_at": "",
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

    def login(self):
        data = request.json
        email = data["email"].lower()
        user = app.db.users.find_one({"email": email})
        if user:
            verify = pbkdf2_sha256.verify(data["password"], user["password"])
            if verify:
                access_token = encodeAccessToken(user["password"], user["email"])

                app.db.users.update_one({"_id": user["_id"]}, {"$set": {
                    "access_token": access_token,
                    "last_login": nowDatetimeUTC()
                }})

                resp = jsonResp({
                    "_id": user["_id"],
                    "email": user["email"],
                    "access_token": access_token,
                }, 200)

                return resp
            else:
                resp = jsonResp({"message": "Password verification failed"}, 200)
                return resp
        else:
            resp = jsonResp({"message": "User not found"}, 200)
        return resp

    def logout(self):
        try:
            tokenData = jwt.decode(request.headers.get("AccessToken"), os.environ["SECRET_KEY"])
            app.db.users.update({"id": tokenData["userid"]}, {'$unset': {"access_token": ""}})
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
                access_token =  encodeAccessToken(user["password"], user["email"])
                refresh_token =  encodeRefreshToken(user["password"], user["email"])

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
