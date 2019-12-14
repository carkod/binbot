from flask import Flask
from flask import Blueprint
from flask import current_app as app
from flask_cors import CORS, cross_origin
from main.userDataStream.models import UserDataStream

user_datastream_blueprint = Blueprint("user-data-stream", __name__)

@user_datastream_blueprint.route("/", methods=["GET"])
def get():
  return UserDataStream().post_user_datastream()

# @userDataStream_blueprint.route("/listenkey", methods=["GET"])
# def get_listenkey():
# 	return UserDataStream().get_listenkey()
