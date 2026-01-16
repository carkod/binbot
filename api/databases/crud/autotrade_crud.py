from databases.tables.autotrade_table import (
    AutotradeTable,
    TestAutotradeTable,
    SettingsDocument,
)
from databases.utils import independent_session
from sqlmodel import Session, select
from sqlmodel.sql._expression_select_cls import SelectOfScalar
from pybinbot import AutotradeSettingsDocument
from autotrade.schemas import AutotradeSettingsSchema, TestAutotradeSettingsSchema


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
        if session is None:
            session = independent_session()
        self.session = session

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

        results = self.session.exec(statement)
        # Should always return one result
        settings = results.first()
        assert settings is not None, (
            f"No autotrade settings found for id {self.document_id}"
        )
        self.session.close()
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
        settings = self.session.get(table_class, settings_data.id)

        assert settings is not None, (
            f"No autotrade settings found for id {self.document_id}"
        )
        # start db operations
        settings.sqlmodel_update(data.model_dump())
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        self.session.close()
        return settings

    def get_fiat(self):
        data = self.get_settings()
        return data.fiat
