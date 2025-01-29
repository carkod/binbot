from fastapi import APIRouter, Depends
from user.models.user import CreateUser
from tools.handle_error import json_response, json_response_error
from user.schemas import LoginRequest, UserResponse
from user.services.auth import oauth2_scheme, Token, decode_access_token
from database.user_crud import UserTableCrud
from sqlmodel import Session
from database.utils import get_session

user_blueprint = APIRouter()


@user_blueprint.get("/user", response_model=UserResponse, tags=["users"])
def get(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    """
    Get all users
    """
    decode_access_token(token)
    return UserTableCrud(session).get()


@user_blueprint.get("/user/{email}", response_model=UserResponse, tags=["users"])
def get_one(email: str, session: Session = Depends(get_session)):
    """
    Get user by email
    """
    return UserTableCrud(session).get_one(email)


@user_blueprint.post("/user/login", tags=["users"], response_model=Token)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    """
    Get an access_token to keep the user in session
    """
    try:
        access_token, user_data = UserTableCrud(session).login(data)
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
def add(data: CreateUser, session: Session = Depends(get_session)):
    """
    Create/register a new user
    """
    return UserTableCrud(session).add(data)


@user_blueprint.put("/user", tags=["users"])
def edit(user: CreateUser, session: Session = Depends(get_session)):
    """
    Modify details of a user that already exists.
    If the user does not exist, it will return a JSON error message
    """
    return UserTableCrud(session).edit(user)


@user_blueprint.delete("/user/{email}", tags=["users"])
def delete(email: str, session: Session = Depends(get_session)):
    """
    Delete a user by email
    """
    return UserTableCrud(session).delete(email)
