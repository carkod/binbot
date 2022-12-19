from flask import current_app
from api.research.schemas import AutotradeSettingsSchema
from api.tools.handle_error import json_response, json_response_error, json_response_message
from flask import current_app, request
from marshmallow.exceptions import ValidationError

class AutotradeSettingsController:
    """
    Autotrade settings

    Args:
    - document_id [string]: OneOf["test_autotrade_settings", "settings"]
    """

    def __init__(self, document_id="settings"):
        self.document_id = document_id

    def get_settings(self):
        try:
            settings = current_app.db.research_controller.find_one({"_id": self.document_id})
            resp = json_response(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        except Exception as error:
            resp = json_response_error(f"Error getting settings: {error}")

        return resp

    def edit_settings(self):
        data = request.get_json()
        try:
            settings_schema = AutotradeSettingsSchema()
            settings = settings_schema.load(data)
            if "_id" in settings:
                settings.pop("_id")
            if "update_required" in settings and settings["update_required"] == False:
                settings["update_required"] = True

            current_app.db.research_controller.update_one({"_id": self.document_id}, {"$set": settings})
            resp = json_response_message("Successfully updated settings")
        except TypeError as e:
            resp = json_response_error(f"Data validation error: {e}")
        except ValidationError as error:
            msg = ""
            for field, desc in error.args[0].items():
                msg += field + desc[0]
            resp = json_response_error(f"{msg}")
        return resp
