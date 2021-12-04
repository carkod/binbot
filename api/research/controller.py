from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from flask import current_app, request
from pymongo.errors import DuplicateKeyError
from api.research.controller_schema import ControllerSchema


class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        self.default_blacklist = {"_id": "", "pair": "", "reason": ""}  # pair

    def get_settings(self):
        settings = ControllerSchema().get()

        if settings:
            resp = jsonResp(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        else:
            resp = jsonResp_error_message(
                "Database error ocurred. Could not retrieve settings."
            )
        return resp

    def edit_settings(self):
        data = request.get_json()
        controller_schema = ControllerSchema()
        try:
            controller_schema.update(data)
            resp = jsonResp_message("Successfully updated settings")
        except TypeError as e:
            resp = jsonResp_error_message(f"Data validation error: {e}")
        return resp

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
