from unittest.mock import MagicMock

from api.databases.api_db import ApiDb
from api.databases.tables.autotrade_table import AutotradeTable


def test_init_autotrade_settings_creates_document_from_model_defaults():
    session = MagicMock()
    session.exec.return_value.first.return_value = None
    api_db = object.__new__(ApiDb)
    api_db.session = session

    api_db.init_autotrade_settings()

    settings = session.add.call_args.args[0]
    assert isinstance(settings, AutotradeTable)
    assert settings.id == "autotrade_settings"
    assert settings.autotrade is False
    assert settings.fiat == "USDC"
    session.commit.assert_called_once_with()


def test_init_autotrade_settings_preserves_existing_document():
    session = MagicMock()
    session.exec.return_value.first.return_value = AutotradeTable(autotrade=True)
    api_db = object.__new__(ApiDb)
    api_db.session = session

    api_db.init_autotrade_settings()

    session.add.assert_not_called()
    session.commit.assert_not_called()
