from sqlmodel import select
from database.api_db import ApiDb
from database.models.autotrade_table import AutotradeTable, TestAutotradeTable
from autotrade.schemas import AutotradeSettingsSchema
from base_producer import BaseProducer
from tools.enum_definitions import AutotradeSettingsDocument


class AutotradeSettingsController:
    """
    Autotrade settings
    """

    def __init__(
        self,
        document_id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings,
    ):
        self.document_id = document_id
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()
        self.db = ApiDb()
        self.session = self.db.session
        if document_id == AutotradeSettingsDocument.settings:
            self.table = AutotradeTable
        if document_id == AutotradeSettingsDocument.test_autotrade_settings:
            self.table = TestAutotradeTable

    def get_settings(self):
        statement = select(AutotradeTable).where(AutotradeTable.id == self.document_id)
        results = self.session.exec(statement)
        # Should always return one result
        settings = results.first()
        return settings

    def edit_settings(self, data):
        settings_data = AutotradeSettingsSchema.model_validate(data)
        settings = self.session.get(self.table, settings_data.id)

        if not settings:
            return settings

        # start db operations
        settings.sqlmodel_update(settings.model_dump(exclude_unset=True))
        self.session.add(settings)
        self.session.commit()

        # end of db operations
        # update the producer to reload streaming data
        self.base_producer.update_required(self.producer, "UPDATE_AUTOTRADE_SETTINGS")
        return settings
