from fastapi import APIRouter, Depends
from fastapi.exceptions import ResponseValidationError
from user.models.user import UserDetails
from tools.handle_error import json_response, StandardResponse
from user.models.user import LoginRequest, UserResponse, GetOneUser
from user.services.auth import Auth, TokenResponse, decode_access_token
from database.user_crud import UserTableCrud
from sqlmodel import Session
from database.utils import get_session
from sqlalchemy.exc import IntegrityError

user_blueprint = APIRouter()


@user_blueprint.get("/user", response_model=UserResponse, tags=["users"])
def get(session: Session = Depends(get_session)):
    """
    Get all users
    """
    # decode_access_token(token)
    all_users = UserTableCrud(session).get()
    return UserResponse(message="Users found!", data=all_users)


@user_blueprint.get("/user/{email}", response_model=GetOneUser, tags=["users"])
def get_one(email: str, session: Session = Depends(get_session)):
    """
    Get user by email
    """
    try:
        user = UserTableCrud(session).get_one(email=email)
        return GetOneUser(message="User found!", data=user)
    except ResponseValidationError as e:
        return StandardResponse(message=str(e), error=1)


@user_blueprint.post("/user/login", tags=["users"], response_model=TokenResponse)
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
        return StandardResponse(str(e))


@user_blueprint.post("/user/register", response_model=GetOneUser | StandardResponse, tags=["users"])
def add(data: UserDetails, session: Session = Depends(get_session)):
    """
    Create/register a new user
    """
    try:
        added_user = UserTableCrud(session).add(data)
        return GetOneUser(message="Added new user!", data=added_user)
    except IntegrityError as error:
        return StandardResponse(message=str(error), error=1)


@user_blueprint.put("/user", response_model=GetOneUser | StandardResponse, tags=["users"])
def edit(user: UserDetails, session: Session = Depends(get_session)):
    """
    Modify details of a user that already exists.
    If the user does not exist, it will return a JSON error message
    """
    try:
        edited_user = UserTableCrud(session).edit(user)
        return GetOneUser(message=f"Edited user {edited_user.email}!", data=edited_user)
    except ResponseValidationError as e:
        return StandardResponse(message=str(e), error=1)


@user_blueprint.delete("/user/{email}", tags=["users"])
def delete(email: str, session: Session = Depends(get_session)):
    """
    Delete a user by email
    """
    try:
        UserTableCrud(session).delete(email)
        return StandardResponse(message="Deleted user!")
    except ResponseValidationError as e:
        return StandardResponse(message=str(e), error=1)
