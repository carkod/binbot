import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FUTURES_BRIDGE = REPOSITORY_ROOT / "api/exchange_apis/kucoin/futures"


def test_kucoin_futures_bridge_does_not_import_streaming() -> None:
    offenders: list[str] = []

    for path in FUTURES_BRIDGE.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue

            if any(
                module == "streaming" or module.startswith("streaming.")
                for module in modules
            ):
                offenders.append(str(path.relative_to(REPOSITORY_ROOT)))

    assert offenders == []


def test_lifecycle_and_position_market_are_streaming_owned() -> None:
    assert (REPOSITORY_ROOT / "streaming/lifecycle.py").is_file()
    assert (REPOSITORY_ROOT / "streaming/position_market.py").is_file()
    assert not (FUTURES_BRIDGE / "lifecycle.py").exists()
    assert not (FUTURES_BRIDGE / "position_market.py").exists()
