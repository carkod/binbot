from flask import Flask
from flask import Blueprint
from flask import current_app as app
from main.auth import token_required
from main.account.models import Account
from flask_cors import CORS, cross_origin


# initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
app.config['CORS_HEADERS'] = 'Content-Type'

cors = CORS(app, resources={r"/user": {"origins": "http://localhost:5000"}})

account_blueprint = Blueprint("account", __name__)
# @token_required
@account_blueprint.route("/", methods=["GET"])
def get():
	return Account().get_balances()

@account_blueprint.route("/balance", methods=["GET"])
def getAuth():
	return Account().get_balances()

