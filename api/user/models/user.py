from datetime import date
from passlib.hash import pbkdf2_sha256
from tools.handle_error import (
    json_response_error,
    json_response_message,
    json_response,
)
from bson.objectid import ObjectId
from auth import encode_access_token
from database.mongodb.db import setup_db
from user.schemas import UserSchema
from fastapi.encoders import jsonable_encoder


class User:
    def __init__(self):
        self.db = setup_db()

    def hash_password(self, password):
        password_bytes = password.encode("utf-8")
        hash_object = pbkdf2_sha256.encrypt(password_bytes, rounds=20000, salt_size=16)
        return hash_object.hexdigest()

    def get(self):
        users = list(self.db.users.find())
        if users:
            resp = json_response({"message": "Users found", "data": users})
        else:
            resp = json_response_message("No users found")

        return resp

    def get_one(self, email):
        user = self.db.users.find_one({"email": email})

        if user:
            resp = json_response({"message": "User found", "data": user})
        else:
            resp = json_response({"message": "User not found", "error": 1}, 401)
        return resp

    def login(self, data):
        """
        Provided email and password, returns token to login
        """
        email = data.email.lower()
        password = data.password
        user = self.db.users.find_one({"email": email, "password": password})
        if user:
            access_token, data = encode_access_token(password, email)
            return access_token, data
        else:
            raise Exception("Invalid email or password")

    def add(self, data):
        if (not data.email) or (not data.password):
            return json_response_message("Email and password are required")

        self.defaults = UserSchema(
            email=data.email,
            password=data.password,
            username=data.username,
            description=data.description,
            last_login=date.today().strftime("%Y-%m-%d"),
            created_at=date.today().strftime("%Y-%m-%d"),
        )
        # Merge the posted data with the default user attributes
        self.defaults = self.defaults.copy(update=data.dict(exclude_unset=True))
        # Encrypt the password
        self.defaults.password = pbkdf2_sha256.encrypt(
            self.defaults.password, rounds=20000, salt_size=16
        )
        # Make sure there isn"t already a user with this email address
        existing_email = self.db.users.find_one(
            {"email": jsonable_encoder(self.defaults.email)}
        )

        if existing_email:
            resp = json_response_error(
                "There's already an account with this email address"
            )

        else:
            inserted_doc = self.db.users.insert_one(jsonable_encoder(self.defaults))
            item = self.db.users.find_one({"_id": inserted_doc.inserted_id})
            resp = json_response(
                {"data": item, "message": "Successfully created a new user!"}
            )

        return resp

    def edit(self, data):
        if "email" not in data or "password" not in data:
            return json_response_message("Email and password are required")

        # Merge the posted data with the default user attributes
        self.defaults = self.defaults.copy(update=data.dict(exclude_unset=True))
        # Encrypt the password
        self.defaults.password = pbkdf2_sha256.encrypt(
            self.defaults.password, rounds=20000, salt_size=16
        )

        edit_result = self.db.users.update_one(
            {"email": self.defaults.email}, {"$set": jsonable_encoder(self.defaults)}
        )

        if edit_result:
            return json_response_message("User successfully updated!")
        else:
            return json_response_error("User update failed")

    def delete(self, email):
        count = self.db.users.delete_one({"email": ObjectId(email)}).deleted_count
        if count > 0:
            resp = json_response({"message": "Successfully deleted user"})
        else:
            resp = json_response({"message": "Not found user, cannot delete"})
        return resp
