import os

from flask import Flask, Blueprint
from flask import current_app as app
from main.auth import token_required
from main.account.models import Account
from flask_cors import CORS, cross_origin


# initialization
app = Flask(__name__)
os.environ['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
os.environ['CORS_HEADERS'] = 'Content-Type'

account_blueprint = Blueprint("account", __name__)
# @token_required
@account_blueprint.route("/", methods=["GET"])
def get():
	return Account().get_balances()

@account_blueprint.route("/balance", methods=["GET"])
def getAuth():
	return Account().get_balances()

