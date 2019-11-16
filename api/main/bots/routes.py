from flask import Flask
from flask import Blueprint
from flask import current_app as app
from main.auth import token_required
from main.bots.models import Bot
from flask_cors import CORS, cross_origin


# initialization
# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy   dog'
# app.config['CORS_HEADERS'] = 'Content-Type'

# cors = CORS(app, resources={r"/user": {"origins": "http://localhost:5000"}})

bot_blueprint = Blueprint("bot", __name__)
@bot_blueprint.route("/", methods=["GET"])
def get():
	return Bot().get()

@bot_blueprint.route("/<id>", methods=["GET"])
def get_one(id):
	return Bot().get_one()

@bot_blueprint.route("/", methods=["POST"])
def create():
	return Bot().create()

@bot_blueprint.route("/", methods=["PUT"])
def edit():
	return Bot().edit()

@bot_blueprint.route("/<id>", methods=["DELETE"])
def delete(id):
	return Bot().delete(id)

@bot_blueprint.route("/activate/<botId>", methods=["GET"])
def activate(botId):
	return Bot().activate()


@bot_blueprint.route("/deactivate/<botId>", methods=["GET"])
def deactivate(botId):
	return Bot().deactivate()