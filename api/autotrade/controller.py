import typing

from base_producer import AsyncBaseProducer
from database.models.autotrade_table import AutotradeTable, TestAutotradeTable
from database.utils import independent_session
from sqlmodel import Session, select
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

    @typing.no_type_check
    def get_settings(self):
        """
        Mypy check ignored: Incompatible types in assignment
        should not affect execution of statement.
        This is to avoid dup code
        """
        if self.document_id == AutotradeSettingsDocument.test_autotrade_settings:
            statement = select(TestAutotradeTable).where(
                TestAutotradeTable.id == self.document_id
            )
        else:
            statement = select(AutotradeTable).where(
                AutotradeTable.id == self.document_id
            )

        results = self.session.exec(statement)
        # Should always return one result
        settings = results.first()
        self.session.close()
        return settings

    @typing.no_type_check
    def edit_settings(self, data):
        """
        Mypy check ignored: Incompatible types in assignment
        should not affect execution of statement.
        This is to avoid dup code
        """
        if self.document_id == AutotradeSettingsDocument.test_autotrade_settings:
            settings_data = TestAutotradeTable.model_validate(data)
            settings = self.session.get(TestAutotradeTable, settings_data.id)
        else:
            settings_data = AutotradeTable.model_validate(data)
            settings = self.session.get(AutotradeTable, settings_data.id)

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
        self.session.close()
        return settings

    def get_fiat(self):
        data = self.get_settings()
        return data.fiat
