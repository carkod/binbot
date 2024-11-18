from fastapi import APIRouter

from apis import ThreeCommasApi
from research.controller import Controller
from research.schemas import BlacklistSchema, BlacklistResponse, SubscribedSymbolsSchema
from tools.handle_error import json_response

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


@research_blueprint.get(
    "/blacklist", response_model=BlacklistResponse, tags=["blacklist and research"]
)
def get_blacklisted():
    """
    Get all symbols/pairs blacklisted
    """
    data = Controller().get_blacklist()
    return json_response({"message": "Successfully retrieved blacklist", "data": data})


@research_blueprint.get("/3commas-presets", tags=["blacklist and research"])
def three_commas_presets():
    return ThreeCommasApi().get_marketplace_presets()


@research_blueprint.get("/subscribed", tags=["blacklist and research"])
def get_subscribed_symbols():
    return Controller().get_subscribed_symbols()


@research_blueprint.post("/subscribed", tags=["blacklist and research"])
def create_subscribed_symbols(data: list[SubscribedSymbolsSchema]):
    return Controller().bulk_upsert_all(data)


@research_blueprint.put("/subscribed/{symbol}", tags=["blacklist and research"])
def edit_subscribed_symbol(symbol: str):
    return Controller().edit_subscribed_symbol(symbol)
