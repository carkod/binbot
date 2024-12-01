from sqlmodel import Session, select
from database.utils import independent_session
from database.models.autotrade_table import AutotradeTable, TestAutotradeTable
from autotrade.schemas import AutotradeSettingsSchema
from base_producer import AsyncBaseProducer
from tools.enum_definitions import AutotradeSettingsDocument


class AutotradeSettingsController:
    """
    Autotrade settings
    """

    def __init__(
        self,
        # Some instances of AutotradeSettingsController are used outside of the FastAPI context
        # this is designed this way for reusability
        session: Session | None = None,
        document_id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings,
    ):
        self.document_id = document_id
        if session is None:
            session = independent_session()

        self.session = session
        if document_id == AutotradeSettingsDocument.settings:
            self.table = AutotradeTable
        if document_id == AutotradeSettingsDocument.test_autotrade_settings:
            self.table = TestAutotradeTable

    def get_settings(self):
        statement = select(self.table).where(self.table.id == self.document_id)
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
        dumped_settings = settings.model_dump(exclude_unset=True)
        settings.sqlmodel_update(dumped_settings)
        self.session.add(settings)
        self.session.commit()

        # end of db operations
        # update the producer to reload streaming data
        AsyncBaseProducer().update_required("UPDATE_AUTOTRADE_SETTINGS")
        return settings
