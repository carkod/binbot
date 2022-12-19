from fastapi import APIRouter
from api.apis import ThreeCommasApi
from api.research.controller import Controller
from api.auth import auth

research_blueprint = APIRouter()


@research_blueprint.post("/blacklist")
def post_blacklist():
    return Controller().create_blacklist_item()


@research_blueprint.delete("/blacklist/<pair>")
def delete_blacklist_item(pair):
    return Controller().delete_blacklist_item()


@research_blueprint.put("/blacklist")
def put_blacklist():
    return Controller().edit_blacklist()


@research_blueprint.get("/blacklist")
def get_blacklisted():
    return Controller().get_blacklist()


@research_blueprint.get("/3commas-presets")
@auth.login_required
def three_commas_presets():
    return ThreeCommasApi().get_marketplace_presets()


@research_blueprint.get("/3commas-items")
@auth.login_required
def three_commas_items():
    return Controller().get_profitable_signals()
