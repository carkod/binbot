from flask import request, current_app as app
from passlib.hash import pbkdf2_sha256
from jose import jwt
import os
from api.tools.handle_error import json_response_error, json_response_message, json_response
from bson.objectid import ObjectId
from api.auth import encodeAccessToken
from datetime import datetime


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
        users = list(app.db.users.find())
        if users:
            resp = json_response({"message": "Users found", "data": users})
        else:
            resp = json_response_message("No users found")

        return resp

    def get_one(self):
        findId = request.view_args["id"]
        user = app.db.users.find_one({"_id": ObjectId(findId)})

        if user:
            resp = json_response({"message": "User found", "data": user})
        else:
            resp = json_response({"message": "User not found", "error": 1}, 401)
        return resp

    def login(self):
        data = request.get_json()
        email = data["email"].lower()
        user = app.db.users.find_one({"email": email})
        if user:
            access_token = encodeAccessToken(user["password"], user["email"])
            app.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "access_token": access_token,
                        "last_login": datetime.now(),
                    }
                },
            )

            resp = json_response(
                {
                    "_id": user["_id"],
                    "email": user["email"],
                    "access_token": access_token,
                    "error": 0,
                },
                200,
            )
        else:
            resp = json_response({"message": "Credentials are incorrect", "error": 1})
        return resp

    def logout(self):
        try:
            tokenData = jwt.decode(
                request.headers.get("AccessToken"), os.environ["SECRET_KEY"]
            )
            app.db.users.update(
                {"id": tokenData["userid"]}, {"$unset": {"access_token": None}}
            )
            # Note: At some point I need to implement Token Revoking/Blacklisting
            # General info here: https://flask-jwt-extended.readthedocs.io/en/latest/blacklist_and_token_revoking.html
        except Exception as error:
            raise Exception(error)

        resp = json_response_message("User logged out")

        return resp

    def add(self):
        try:
            data = request.json
        except TypeError as e:
            print(e)
            return json_response_error("Json data is malformed")
        if ("email" not in data) or ("password" not in data):
            return json_response_message("Email and password are required")

        user_data = {
            "email": data["email"].lower(),
            "password": data["password"],
            "username": data["username"],
            "description": data["description"],
        }
        # Merge the posted data with the default user attributes
        self.defaults.update(user_data)
        # Encrypt the password
        self.defaults["password"] = pbkdf2_sha256.encrypt(
            user_data["password"], rounds=20000, salt_size=16
        )
        # Make sure there isn"t already a user with this email address
        existing_email = app.db.users.find_one({"email": self.defaults["email"]})

        if existing_email:
            resp = json_response_error(
                "There's already an account with this email address"
            )

        else:
            inserted_doc = app.db.users.insert_one(self.defaults)
            item = app.db.users.find_one({"_id": inserted_doc.inserted_id})
            resp = json_response(
                {"data": item, "message": "Successfully created a new user!"}
            )

        return resp

    def edit(self):
        try:
            data = request.get_json()
        except TypeError:
            return json_response_error("Json data is malformed")
        if "email" not in data or "password" not in data:
            return json_response_message("Email and password are required")

        user_data = {
            "email": data["email"].lower(),
            "password": data["password"],
            "username": data["username"],
            "description": data["description"],
        }
        # Merge the posted data with the default user attributes
        self.defaults.update(user_data)
        user = self.defaults
        # Encrypt the password
        user["password"] = pbkdf2_sha256.encrypt(
            user["password"], rounds=20000, salt_size=16
        )

        edit_result = app.db.users.update_one({"email": user["email"]}, {"$set": user})

        if edit_result:
            return json_response_message("User successfully updated!")
        else:
            return json_response_error("User update failed")

    def delete(self):
        findId = request.view_args["id"]
        count = app.db.users.delete_one({"_id": ObjectId(findId)}).deleted_count
        if count > 0:
            resp = json_response({"message": "Successfully deleted user"})
        else:
            resp = json_response({"message": "Not found user, cannot delete"})
        return resp
