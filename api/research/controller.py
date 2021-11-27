from typing import List
from api.tools.handle_error import jsonResp
from flask import current_app, request
from pymongo.errors import DuplicateKeyError

# class ControllerModel:
#     def __init__(self) -> object:
#         self.defaults = {
#             "candlestick_interval": "1h",
#             "autotrade": 0,
#             "trailling_profit": 2.4,
#             "stop_loss": 3,
#             "trailling": "true",
#             "trailling_deviation": "3",
#             "update_required": False,  # Changed made, need to update websockets
#             "balance_to_use": "BNB",
#             "balance_size_to_use": 100,  # %
#             "max_request": 950,
#             "system_logs": [],
#             "errors": [],
#         }

#     def update(self, *args):
#         self.defaults = {
#             "candlestick_interval": args.__getitem__("candlestick_interval"),
#             "autotrade": 0,
#             "trailling_profit": 2.4,
#             "stop_loss": 3,
#             "trailling": "true",
#             "trailling_deviation": "3",
#             "update_required": False,  # Changed made, need to update websockets
#             "balance_to_use": "BNB",
#             "balance_size_to_use": 100,  # %
#             "max_request": 950,
#             "system_logs": [],
#             "errors": [],
#         }


class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        # Data model
        self.defaults = {
            "candlestick_interval": "1h",
            "autotrade": 0,
            "trailling_profit": 2.4,
            "stop_loss": 3,
            "trailling": "true",
            "trailling_deviation": "3",
            "update_required": False,  # Changed made, need to update websockets
            "balance_to_use": "BNB",
            "balance_size_to_use": 100,  # %
            "max_request": 950,
            "system_logs": [],
            "errors": [],
        }
        self.default_blacklist = {"_id": "", "pair": "", "reason": ""}  # pair

    def get_settings(self):
        settings = current_app.db.research_controller.find_one({"_id": "settings"})

        # Should never be empty,
        # It will be used in the future for research control
        if (
            not settings
            or "candlestick_interval" not in settings
            or "autotrade" not in settings
        ):
            current_app.db.research_controller.insert(
                {"_id": "settings"}, self.defaults
            )

        resp = jsonResp(
            {"message": "Successfully retrieved settings", "data": settings}
        )
        return resp

    def edit_settings(self):
        # Start with current settings
        self.defaults.update(current_app.db.research_controller.find_one({"_id": "settings"}))
        data = request.get_json()

        if "system_logs" in data and isinstance(self.defaults["system_logs"], str):
            self.defaults["system_logs"].extend(data["system_logs"])

        if isinstance(self.defaults["update_required"], str) and self.defaults["update_required"].lower() == "true":
            self.defaults["update_required"] = True

        self.defaults.update(data)
        self.defaults["errors"] = []
        self.defaults.pop("_id")
        current_app.db.research_controller.update_one(
            {"_id": "settings"}, {"$set": self.defaults}, True
        )
        return jsonResp({"message": "Successfully updated settings"})

    def get_blacklist(self) -> jsonResp:
        """
        Get list of blacklisted symbols
        """
        blacklist = list(current_app.db.blacklist.find())
        return jsonResp(
            {"message": "Successfully retrieved blacklist", "data": blacklist}
        )

    def create_blacklist_item(self):
        data = request.json
        if "pair" not in data:
            return jsonResp({"message": "Missing required field 'pair'.", "error": 1})

        self.default_blacklist.update(data)
        self.default_blacklist["_id"] = data["pair"]
        try:
            blacklist = current_app.db.blacklist.insert(self.default_blacklist)
        except DuplicateKeyError:
            return jsonResp({"message": "Pair already exists in blacklist", "error": 1})

        if blacklist:
            resp = jsonResp(
                {"message": "Successfully updated blacklist", "data": blacklist}
            )
        else:
            resp = jsonResp({"message": "Failed to update blacklist", "error": 1})

        return resp

    def delete_blacklist_item(self):
        pair = request.view_args["pair"]

        blacklist = current_app.db.blacklist.delete_one({"_id": pair})

        if blacklist.acknowledged:
            resp = jsonResp({"message": "Successfully updated blacklist"})
        else:
            resp = jsonResp({"message": "Item does not exist", "error": 1})

        return resp

    def edit_blacklist(self):
        data = request.json
        if "pair" not in data:
            return jsonResp({"message": "Missing required field 'pair'.", "error": 1})

        self.default_blacklist.update(data)
        blacklist = current_app.db.blacklist.find_one_and_update(
            {"_id": data["pair"]}, {"$set": self.default_blacklist}
        )

        if not blacklist:
            current_app.db.blacklist.insert(self.default_blacklist)

        resp = jsonResp(
            {"message": "Successfully updated blacklist", "blacklist": blacklist}
        )
        return resp
