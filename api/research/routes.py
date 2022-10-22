from flask import Blueprint
from api.apis import ThreeCommasApi
from api.research.controller import Controller
from api.auth import auth

research_blueprint = Blueprint("research", __name__)


@research_blueprint.route("/blacklist", methods=["POST"])
def post_blacklist():
    return Controller().create_blacklist_item()


@research_blueprint.route("/blacklist/<pair>", methods=["DELETE"])
def delete_blacklist_item(pair):
    return Controller().delete_blacklist_item()


@research_blueprint.route("/blacklist", methods=["PUT"])
def put_blacklist():
    return Controller().edit_blacklist()


@research_blueprint.route("/blacklist", methods=["GET"])
def get_blacklisted():
    return Controller().get_blacklist()


@research_blueprint.route("/3commas-presets", methods=["GET"])
@auth.login_required
def three_commas_presets():
    return ThreeCommasApi().get_marketplace_presets()


@research_blueprint.route("/3commas-items", methods=["GET"])
@auth.login_required
def three_commas_items():
    return Controller().get_profitable_signals()
