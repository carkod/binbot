from flask import Blueprint, Flask
from flask import current_app as app
from flask_cors import CORS, cross_origin

from main.userDataStream.controllers import UserDataStream

user_datastream_blueprint = Blueprint("user-data-stream", __name__)


@user_datastream_blueprint.route("/", methods=["GET"])
def get():
    return UserDataStream().post_user_datastream()


@user_datastream_blueprint.route("/update-orders", methods=["GET"])
def order_update():
    return UserDataStream().order_update()
