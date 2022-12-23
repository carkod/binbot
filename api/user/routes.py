from fastapi import APIRouter

from api.auth import auth
from api.user.models.user import User
from api.user.schemas import UserSchema, LoginRequest, UserResponse

user_blueprint = APIRouter()


@user_blueprint.get("/user", response_model=UserResponse, tags=["users"])
def get():
    """
    Get all users
    """
    return User().get()


@user_blueprint.get("/user/{email}", response_model=UserResponse, tags=["users"])
def get_one(email):
    """
    Get user by email
    """
    return User().get_one(email)


@user_blueprint.post("/user/login", tags=["users"])
def login(data: LoginRequest):
    """
    Get an access_token to keep the user in session
    """
    return User().login(data)


@user_blueprint.get("/user/logout", tags=["users"])
def logout():
    """
    Remove access_token
    """
    return User().logout()


@user_blueprint.post("/user/register", tags=["users"])
def add(data: UserSchema):
    """
    Create/register a new user
    """
    return User().add(data)


@user_blueprint.put("/user", tags=["users"])
def edit(user: UserSchema):
    """
    Modify details of a user that already exists.
    If the user does not exist, it will return a JSON error message
    """
    return User().edit(user)


@user_blueprint.delete("/user/{email}", tags=["users"])
def delete(email: str):
    """
    Delete a user by email
    """
    return User().delete(email)
