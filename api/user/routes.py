from flask import Blueprint
from api.user.models.user import User
from api.auth import auth

user_blueprint = Blueprint("user", __name__)


@user_blueprint.route("/user", methods=["GET"])
@auth.login_required
def get():
    return User().get()


@user_blueprint.route("/user/<id>", methods=["GET"])
@auth.login_required
def get_one(id):
    return User().get_one()


@user_blueprint.route("/user/login", methods=["POST"])
def login():
    return User().login()


@user_blueprint.route("/user/logout", methods=["GET"])
def logout():
    return User().logout()


@user_blueprint.route("/user/register", methods=["POST"])
@auth.login_required
def add():
    return User().add()

@user_blueprint.route("/user/<id>", methods=["PUT"])
@auth.login_required
def edit(id):
    return User().edit()

@user_blueprint.route("/user/<id>", methods=["DELETE"])
@auth.login_required
def delete(id):
    return User().delete()
