import logging
import os
import time
from typing import Iterable

DEFAULT_FORMAT = "%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    *,
    level: str | None = None,
    fmt: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATEFMT,
    utc: bool = True,
    force: bool = True,
    quiet_loggers: Iterable[str] | None = ("uvicorn", "confluent_kafka"),
) -> None:
    """
    Configure root logging consistently across API services.
    """
    resolved_level = str(level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=resolved_level,
        format=fmt,
        datefmt=datefmt,
        force=force,
    )
    if utc:
        logging.Formatter.converter = time.gmtime

    if quiet_loggers:
        quiet_level = os.environ.get("QUIET_LIB_LOG_LEVEL", "WARNING").upper()
        for name in quiet_loggers:
            logging.getLogger(name).setLevel(quiet_level)

    logging.getLogger(__name__).debug(
        "Logging configured (level=%s, utc=%s, force=%s)",
        resolved_level,
        utc,
        force,
    )
