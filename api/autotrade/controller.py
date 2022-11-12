from flask import current_app
from api.research.schemas import AutotradeSettingsSchema
from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from flask import current_app, request


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
            resp = jsonResp(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        except Exception as error:
            resp = jsonResp_error_message(f"Error getting settings: {error}")

        return resp

    def edit_settings(self):
        data = request.get_json()
        try:
            settings_schema = AutotradeSettingsSchema()
            settings = settings_schema.load(data)
            if "_id" in settings:
                settings.pop("_id")
            current_app.db.research_controller.update_one({"_id": self.document_id}, {"$set": settings})
            resp = jsonResp_message("Successfully updated settings")
        except TypeError as e:
            resp = jsonResp_error_message(f"Data validation error: {e}")
        return resp
