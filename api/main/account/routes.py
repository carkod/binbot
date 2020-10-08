import os

from flask import Blueprint
from main.account.models import Account


# initialization
os.environ['CORS_HEADERS'] = 'Content-Type'

account_blueprint = Blueprint("account", __name__)
# @token_required


@account_blueprint.route("/", methods=["GET"])
def get():
	return Account().get_balances()


@account_blueprint.route("/balance", methods=["GET"])
def getAuth():
	return Account().get_balances()
