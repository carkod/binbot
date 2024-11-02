from pydantic import ValidationError
from api.autotrade.schemas import AutotradeSettingsSchema
from base_producer import BaseProducer
from database.mongodb.db import Database
from tools.handle_error import (
    json_response_error,
    json_response_message,
)
from tools.enum_definitions import AutotradeSettingsDocument


class AutotradeSettingsController(Database):
    """
    Autotrade settings
    """

    def __init__(
        self,
        document_id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings,
    ):
        self.document_id = document_id
        self.db = self._db
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()

    def get_settings(self):
        settings = self.db.research_controller.find_one({"_id": self.document_id})
        deserialized_data = AutotradeSettingsSchema(**settings)
        return deserialized_data

    def edit_settings(self, data):
        try:
            self.db.research_controller.update_one(
                {"_id": self.document_id}, {"$set": data.model_dump()}
            )
            self.base_producer.update_required(
                self.producer, "UPDATE_AUTOTRADE_SETTINGS"
            )
            resp = json_response_message("Successfully updated settings")
        except TypeError as e:
            resp = json_response_error(f"Data validation error: {e}")
        except ValidationError as error:
            msg = ""
            for field, desc in error.args[0].items():
                msg += field + desc[0]
            resp = json_response_error(f"{msg}")
        return resp
