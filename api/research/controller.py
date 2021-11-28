import numbers

from _typeshed import NoneType
from api.tools.enum_definitions import EnumDefinitions
from api.tools.handle_error import jsonResp, jsonResp_error_message
from flask import current_app, request
from pymongo.errors import DuplicateKeyError

class NewFieldError(Exception):
    pass

class ControllerSchema:
    """
    Centralizes the data structure 
    - to protect the MongoDB from inconsistencies setting old and new fields
    - validation of fields and types

    """
    def __init__(self) -> object:
        self.candlestick_interval = "1h"
        self.autotrade = 0
        self.trailling = "true"
        self.trailling_deviation = 3
        self.trailling_profit = 2.4
        self.stop_loss = 3
        self.balance_to_use = "GBP"
        self.balance_size_to_use = 100
        self.max_request = 950
        self.system_logs = []
        self.errors = []

    def validate_model(self, raw):

        data = raw

        if not isinstance(data.get("candlestick_interval"), str) and data.get("candlestick_interval") not in EnumDefinitions.chart_intervals:
            raise TypeError(f"candlestick_interval must be a String value among these {str(EnumDefinitions.chart_intervals)}")
        elif not isinstance(data.get("candlestick_interval"), NoneType):
            self.candlestick_interval = data.get("candlestick_interval")
        
        if not isinstance(data.get("autotrade"), int) and data.get("autotrade") not in [0, 1]:
            raise TypeError(f"autotrade must be a Integer 0 or 1")
        elif not isinstance(data.get("autotrade"), NoneType):
            self.autotrade = data.get("autotrade")


        if not isinstance(data.get("trailling"), int) and data.get("trailling") not in ["true", "false"]:
            raise TypeError(f"trailling must be a String true or false")
        elif not isinstance(data.get("trailling"), NoneType):
            self.trailling = data.get("trailling")

        if not isinstance(data.get("stop_loss"), (int, float)):
            raise TypeError(f"stop_loss must be a Real number")
        elif not isinstance(data.get("stop_loss"), NoneType):
            self.stop_loss = data.get("stop_loss")


        if not isinstance(data.get("trailling_deviation"), (int, float)):
            raise TypeError(f"trailling_deviation must be a Real number")
        elif not isinstance(data.get("trailling_deviation"), NoneType):
            self.trailling_deviation = data.get("trailling_deviation")
        
        if not isinstance(data.get("update_required"), bool):
            raise TypeError(f"update_required must be a Python boolean")
        elif not isinstance(data.get("update_required"), NoneType):
            self.update_required = data.get("update_required")

        if not isinstance(data.get("balance_to_use"), int) and 1 <= data.get("balance_to_use") <= 100:
            raise TypeError(f"balance_to_use must be a positive integer between 0 and 100")
        elif not isinstance(data.get("balance_to_use"), NoneType):
            self.balance_to_use = data.get("balance_to_use")

        
        if not isinstance(data.get("max_request"), int):
            raise TypeError(f"max_request must be a Real number")
        elif not isinstance(data.get("max_request"), NoneType):
            self.max_request = data.get("max_request")
        

        if not isinstance(data.get("system_logs"), int):
            raise TypeError(f"system_logs must be a Real number")
        elif not isinstance(data.get("system_logs"), NoneType):
            self.system_logs = data.get("system_logs")
        
        delattr(data, "candlestick_interval")
        delattr(data, "autotrade")
        delattr(data, "trailling")
        delattr(data, "stop_loss")
        delattr(data, "trailling_deviation")
        delattr(data, "update_required")
        delattr(data, "balance_to_use")
        delattr(data, "max_request")
        delattr(data, "system_logs")

        if len(data) > 0:
            for item in data:
                raise NewFieldError(f"{item} was not found. If this is a new field, please add it to the ControllerSchema")
        
        return True
    
    def update(self, data):
        """Insert logic"""

        validation = self.validate_model(data)
        if validation:
            clean_data = self.__dict__
            current_app.db.research_controller.update_one({"_id": "settings"}, clean_data, True)
            return True
        else:
            return False
    
    def create(self):
        current_app.db.research_controller.insert_one({"_id": "settings"}, self.__dict__)

class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
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
            ControllerSchema.create()

        if settings:
            resp = jsonResp(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        else:
            resp = jsonResp_error_message("Database error ocurred. Could not retrieve settings.")
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
