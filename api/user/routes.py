from fastapi import APIRouter, Depends
from user.models.user import CreateUser
from tools.handle_error import json_response, json_response_error
from user.services.controller import Controller
from user.schemas import LoginRequest, UserResponse
from user.services.auth import oauth2_scheme, Token, decode_access_token

user_blueprint = APIRouter()


@user_blueprint.get("/user", response_model=UserResponse, tags=["users"])
def get(token: str = Depends(oauth2_scheme)):
    """
    Get all users
    """
    decode_access_token(token)
    return Controller().get()


@user_blueprint.get("/user/{email}", response_model=UserResponse, tags=["users"])
def get_one(email):
    """
    Get user by email
    """
    return Controller().get_one(email)


@user_blueprint.post("/user/login", tags=["users"], response_model=Token)
def login(data: LoginRequest):
    """
    Get an access_token to keep the user in session
    """
    try:
        access_token, user_data = Controller().login(data)
        return json_response(
            {
                "message": "Successfully logged in",
                "data": {
                    "access_token": access_token,
                    "expires": user_data["exp"],
                    "email": user_data["email"],
                },
            }
        )
    except Exception as e:
        return json_response_error(str(e))


@user_blueprint.post("/user/register", tags=["users"])
def add(data: CreateUser):
    """
    Create/register a new user
    """
    return Controller().add(data)


@user_blueprint.put("/user", tags=["users"])
def edit(user: CreateUser):
    """
    Modify details of a user that already exists.
    If the user does not exist, it will return a JSON error message
    """
    return Controller().edit(user)


@user_blueprint.delete("/user/{email}", tags=["users"])
def delete(email: str):
    """
    Delete a user by email
    """
    return Controller().delete(email)
