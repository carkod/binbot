from typing import Generator
from unittest.mock import MagicMock, patch


def get_session_mock() -> Generator[MagicMock, None, None]:
    session_mock = MagicMock()
    exec_mock = MagicMock(return_value=True)
    session_mock.configure_mock(**{"exec.return_value": exec_mock})

    with (
        patch("sqlmodel.Session", return_value=session_mock),
    ):
        yield session_mock
