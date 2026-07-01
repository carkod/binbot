from api.databases.tables.autotrade_table import (
    AutotradeTable,
    TestAutotradeTable,
    SettingsDocument,
)
from api.databases.utils import get_db_session
from sqlmodel import Session, select
from sqlmodel.sql._expression_select_cls import SelectOfScalar
from pybinbot import (
    AutotradeSettingsSchema,
    TestAutotradeSettingsSchema,
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

    def get_settings(self) -> AutotradeTable | TestAutotradeTable:
        """
        Mypy check ignored: Incompatible types in assignment
        should not affect execution of statement.
        This is to avoid dup code
        """
        statement: (
            SelectOfScalar[AutotradeTable] | SelectOfScalar[TestAutotradeTable]
        ) = select(AutotradeTable).where(AutotradeTable.id == self.document_id)

        if self.document_id == AutotradeSettingsDocument.test_autotrade_settings:
            statement = select(TestAutotradeTable).where(
                TestAutotradeTable.id == self.document_id
            )

        with get_db_session(self._external_session) as s:
            results = s.exec(statement)
            # Should always return one result
            settings = results.first()
            assert settings is not None, (
                f"No autotrade settings found for id {self.document_id}"
            )
            s.expunge(settings)
            return settings

    def edit_settings(
        self, data: AutotradeSettingsSchema | TestAutotradeSettingsSchema
    ) -> SettingsDocument:
        """
        Edit autotrade settings based on document_id.
        """
        if self.document_id == AutotradeSettingsDocument.test_autotrade_settings:
            table_class: type[TestAutotradeTable | AutotradeTable] = TestAutotradeTable
        else:
            table_class = AutotradeTable

        settings_data = table_class.model_validate(data)
        with get_db_session(self._external_session) as s:
            settings = s.get(table_class, settings_data.id)

            assert settings is not None, (
                f"No autotrade settings found for id {self.document_id}"
            )
            settings.sqlmodel_update(data.model_dump())
            s.add(settings)
            s.commit()
            s.refresh(settings)
            s.expunge(settings)
            return settings

    def get_fiat(self):
        data = self.get_settings()
        return data.fiat
