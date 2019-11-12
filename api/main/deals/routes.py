from flask import Flask
from flask import Blueprint
from flask import current_app as app
from main.auth import token_required
from main.deals.models import Deal
from flask_cors import CORS, cross_origin


# initialization
# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy   dog'
# app.config['CORS_HEADERS'] = 'Content-Type'

# cors = CORS(app, resources={r"/user": {"origins": "http://localhost:5000"}})

deal_blueprint = Blueprint("deal", __name__)
# @token_required
@deal_blueprint.route("/", methods=["GET"])
def get():
	return Deal().get_balances()

@deal_blueprint.route("/balance", methods=["GET"])
def getAuth():
	return Deal().get_balances()

