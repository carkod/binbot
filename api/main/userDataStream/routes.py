from flask import Flask
from flask import Blueprint
from flask import current_app as app
from flask_cors import CORS, cross_origin
# from main.userDataStream.models import UserDataStream

userDataStream_blueprint = Blueprint("user-data-stream", __name__)

# @user_blueprint.route("/listenkey", methods=["POST"])
# @token_required
# def get():
# 	return User().get()

# @userDataStream_blueprint.route("/listenkey", methods=["GET"])
# def get_listenkey():
# 	return UserDataStream().get_listenkey()
