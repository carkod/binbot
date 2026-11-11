from json import loads
from os import environ
from pathlib import Path
from subprocess import run
from sys import executable
from textwrap import dedent


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_importing_streaming_entrypoint_keeps_other_services_eager() -> None:
    result = run(
        [
            executable,
            "-X",
            "lazy_imports=normal",
            "-c",
            dedent("""
                import json
                import sys
                import streaming.main

                print(json.dumps({
                    "mode": sys.get_lazy_imports(),
                    "loaded_pybinbot": "pybinbot" in sys.modules,
                    "loaded_api": "api" in sys.modules,
                }))
            """),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    assert loads(result.stdout) == {
        "mode": "normal",
        "loaded_pybinbot": False,
        "loaded_api": False,
    }


def test_worker_defers_optional_exports_and_registers_database_models() -> None:
    result = run(
        [
            executable,
            "-X",
            "lazy_imports=normal",
            "-c",
            dedent("""
                import builtins
                import sys
                from streaming.main import main

                class WorkerImportsReached(Exception):
                    pass

                original_import = builtins.__import__

                def stop_before_worker_imports(name, *args, **kwargs):
                    if name == "api.databases.utils":
                        assert sys.get_lazy_imports() == "all"
                        raise WorkerImportsReached
                    return original_import(name, *args, **kwargs)

                # Stop before any database or exchange initialization, after
                # verifying that the real entrypoint installed its policy.
                builtins.__import__ = stop_before_worker_imports
                try:
                    main()
                except WorkerImportsReached:
                    pass
                else:
                    raise AssertionError("Worker dependencies were not reached")
                finally:
                    builtins.__import__ = original_import

                import pybinbot
                assert "pybinbot.apis.coingecko" not in sys.modules

                from pybinbot import CoinGecko
                assert CoinGecko.__name__ == "CoinGecko"
                assert "pybinbot.apis.coingecko" in sys.modules

                import api.databases.tables
                from sqlalchemy.orm import configure_mappers
                from sqlmodel import SQLModel

                configure_mappers()
                assert {
                    "bot", "deal", "autotrade", "grid_ladder", "grid_order"
                } <= SQLModel.metadata.tables.keys()

                from kucoin_universal_sdk.generate.futures.market import (
                    GetPartOrderBookReqBuilder,
                )

                request = (
                    GetPartOrderBookReqBuilder()
                    .set_symbol("XBTUSDTM")
                    .set_size("1")
                    .build()
                )
                assert request.model_dump()["symbol"] == "XBTUSDTM"
                print("worker import policy OK")
            """),
        ],
        cwd=REPOSITORY_ROOT,
        env={**environ, "ENV": "ci"},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    assert "worker import policy OK" in result.stdout
