from fastapi import APIRouter

from api.auth import auth
from api.user.models.user import User

user_blueprint = APIRouter()


@user_blueprint.get("/user")
def get():
    return User().get()


@user_blueprint.get("/user/<id>")
def get_one(id):
    return User().get_one()


@user_blueprint.post("/user/login")
def login():
    return User().login()


@user_blueprint.get("/user/logout")
def logout():
    return User().logout()


@user_blueprint.post("/user/register")
def add():
    return User().add()


@user_blueprint.put("/user/<id>")
def edit(id):
    return User().edit()


@user_blueprint.delete("/user/<id>")
def delete(id):
    return User().delete()
