from flask import Blueprint
from api.research.controller import Controller

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


@research_blueprint.route("/controller", methods=["PUT"])
def put_controller():
    return Controller().edit_settings()


@research_blueprint.route("/controller", methods=["GET"])
def get_controller():
    return Controller().get_settings()

@research_blueprint.route("/test-autotrade-settings", methods=["GET"])
def get_test_autotrade_settings():
    return Controller().get_test_autotrade_settings()

@research_blueprint.route("/test-autotrade-settings", methods=["PUT"])
def edit_test_autotrade_settings():
    return Controller().edit_test_autotrade_settings()
