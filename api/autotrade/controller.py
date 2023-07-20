from typing import Literal

from pydantic import ValidationError

from db import setup_db
from tools.handle_error import (
    json_response,
    json_response_error,
    json_response_message,
)
from time import time

class AutotradeSettingsController:
    """
    Autotrade settings
    """

    def __init__(
        self, document_id: Literal["test_autotrade_settings", "settings"] = "settings"
    ):
        self.document_id = document_id
        self.db = setup_db()
        self.db_collection = self.db.research_controller

    def get_settings(self):
        try:
            settings = self.db_collection.find_one({"_id": self.document_id})
            resp = json_response(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        except Exception as error:
            resp = json_response_error(f"Error getting settings: {error}")

        return resp

    def edit_settings(self, data):
        try:
            settings = data.dict()
            if "_id" in settings:
                settings.pop("_id")
            if "update_required" in settings:
                settings["update_required"] = time()

            self.db_collection.update_one({"_id": self.document_id}, {"$set": settings})
            resp = json_response_message("Successfully updated settings")
        except TypeError as e:

            resp = json_response_error(f"Data validation error: {e}")
        except ValidationError as error:
            msg = ""
            for field, desc in error.args[0].items():
                msg += field + desc[0]
            resp = json_response_error(f"{msg}")
        return resp
