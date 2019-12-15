from flask import Flask
from flask import Blueprint
from flask import current_app as app
from flask_cors import CORS, cross_origin
from main.userDataStream.models import UserDataStream
from flask_socketio import send, SocketIO

user_datastream_blueprint = Blueprint("user-data-stream", __name__)

@user_datastream_blueprint.route("/", methods=["GET"])
def get():
  return UserDataStream().post_user_datastream()

@user_datastream_blueprint.route("/update-orders", methods=["GET"])
def order_update():
  return UserDataStream().order_update()


# @userDataStream_blueprint.route("/listenkey", methods=["GET"])
# def get_listenkey():
# 	return UserDataStream().get_listenkey()
