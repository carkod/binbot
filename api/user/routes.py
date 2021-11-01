from flask import Blueprint
from api.user.models.user import User

user_blueprint = Blueprint("user", __name__)


@user_blueprint.route("/", methods=["GET"])
def get():
    return User().get()


@user_blueprint.route("/<id>", methods=["GET"])
def get_one(id):
    return User().get_one()


@user_blueprint.route("/auth/", methods=["GET"])
def getAuth():
    return User().getAuth()


@user_blueprint.route("/login", methods=["POST"])
def login():
    return User().login()


@user_blueprint.route("/logout/", methods=["GET"])
def logout():
    return User().logout()


@user_blueprint.route("/register", methods=["POST"])
def add():
    return User().add()


@user_blueprint.route("/<id>", methods=["DELETE"])
def delete(id):
    return User().delete()


@user_blueprint.route("/datastream", methods=["GET"])
def post():
    return User().post_user_datastream()


@user_blueprint.route("/update-orders", methods=["GET"])
def order_update():
    return User().order_update()
