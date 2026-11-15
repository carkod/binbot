"""Run the collector alone for diagnostics against an isolated database."""

import asyncio
import logging

from streaming.cvd import run

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
asyncio.run(run())
