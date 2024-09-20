from typing import Literal
from pydantic import ValidationError
from base_producer import BaseProducer
from db import Database
from tools.handle_error import (
    json_response,
    json_response_error,
    json_response_message,
)
from tools.enum_definitions import AutotradeSettingsDocument

class AutotradeSettingsController(Database):
    """
    Autotrade settings
    """

    def __init__(
        self, document_id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings
    ):
        self.document_id = document_id
        self.db = self._db
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()


    def get_settings(self):
        try:
            settings = self.db.research_controller.find_one({"_id": self.document_id})
            resp = json_response(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        except Exception as error:
            resp = json_response_error(f"Error getting settings: {error}")

        return resp

    def edit_settings(self, data):
        try:
            self.db.research_controller.update_one({"_id": self.document_id}, {"$set": data.model_dump()})
            self.base_producer.update_required(self.producer, "UPDATE_AUTOTRADE_SETTINGS")
            resp = json_response_message("Successfully updated settings")
        except TypeError as e:
            resp = json_response_error(f"Data validation error: {e}")
        except ValidationError as error:
            msg = ""
            for field, desc in error.args[0].items():
                msg += field + desc[0]
            resp = json_response_error(f"{msg}")
        return resp

    def get_autotrade_settings(self):
        return self._db.research_controller.find_one({"_id": "settings"})

    def get_test_autotrade_settings(self):
        return self._db.research_controller.find_one({"_id": "test_autotrade_settings"})

