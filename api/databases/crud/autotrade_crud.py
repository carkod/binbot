from api.databases.tables.autotrade_table import (
    AutotradeTable,
    SettingsDocument,
)
from api.databases.utils import get_db_session
from sqlmodel import Session, select
from pybinbot import (
    AutotradeSettingsSchema,
    AutotradeSettingsDocument,
)


class AutotradeCrud:
    """
    Database operations for Autotrade settings
    """

    def __init__(
        self,
        # Some instances of AutotradeSettingsController are used outside of the FastAPI context
        # this is designed this way for reusability
        session: Session | None = None,
        document_id: AutotradeSettingsDocument = AutotradeSettingsDocument.settings,
    ):
        self.document_id = document_id
        self._external_session = session

    def get_settings(self) -> AutotradeTable:
        statement = select(AutotradeTable).where(AutotradeTable.id == self.document_id)

        with get_db_session(self._external_session) as s:
            results = s.exec(statement)
            # Should always return one result
            settings = results.first()
            assert settings is not None, (
                f"No autotrade settings found for id {self.document_id}"
            )
            s.expunge(settings)
            return settings

    def edit_settings(self, data: AutotradeSettingsSchema) -> SettingsDocument:
        """
        Edit autotrade settings based on document_id.
        """
        settings_data = AutotradeTable.model_validate(data)
        update_data = data.model_dump(include=data.model_fields_set)
        with get_db_session(self._external_session) as s:
            settings = s.get(AutotradeTable, settings_data.id)

            assert settings is not None, (
                f"No autotrade settings found for id {self.document_id}"
            )
            settings.sqlmodel_update(update_data)
            s.add(settings)
            s.commit()
            s.refresh(settings)
            s.expunge(settings)
            return settings

    def get_fiat(self):
        data = self.get_settings()
        return data.fiat
