from fastapi import APIRouter

from api.apis import ThreeCommasApi
from api.research.controller import Controller
from api.research.schemas import BlacklistSchema, BlacklistResponse

research_blueprint = APIRouter()


@research_blueprint.post("/blacklist", tags=["blacklist and research"])
def post_blacklist(blacklist_item: BlacklistSchema):
    """
    Create a new Blacklist pair item.
    """
    return Controller().create_blacklist_item(blacklist_item)


@research_blueprint.delete("/blacklist/{pair}", tags=["blacklist and research"])
def delete_blacklist_item(pair: str):
    """
    Given symbol/pair, delete an already blacklisted item
    """
    return Controller().delete_blacklist_item(pair)


@research_blueprint.put("/blacklist", tags=["blacklist and research"])
def put_blacklist(blacklist_item: BlacklistSchema):
    """
    Modify a blacklisted item
    """
    return Controller().edit_blacklist(blacklist_item)


@research_blueprint.get("/blacklist", response_model=BlacklistResponse, tags=["blacklist and research"])
def get_blacklisted():
    """
    Get all symbols/pairs blacklisted
    """
    return Controller().get_blacklist()


@research_blueprint.get("/3commas-presets", tags=["blacklist and research"])
def three_commas_presets():
    return ThreeCommasApi().get_marketplace_presets()
