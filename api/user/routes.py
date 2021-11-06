from flask import Blueprint
from api.user.models.user import User
from api.auth import auth

user_blueprint = Blueprint("user", __name__)


@user_blueprint.route("/", methods=["GET"])
@auth.login_required
def get():
    return User().get()


@user_blueprint.route("/<id>", methods=["GET"])
@auth.login_required
def get_one(id):
    return User().get_one()


@user_blueprint.route("/login", methods=["POST"])
def login():
    return User().login()


@user_blueprint.route("/logout/", methods=["GET"])
def logout():
    return User().logout()


@user_blueprint.route("/register", methods=["POST"])
@auth.login_required
def add():
    return User().add()


@user_blueprint.route("/<id>", methods=["DELETE"])
@auth.login_required
def delete(id):
    return User().delete()


@user_blueprint.route("/datastream", methods=["GET"])
def post():
    return User().post_user_datastream()


@user_blueprint.route("/update-orders", methods=["GET"])
def order_update():
    return User().order_update()
