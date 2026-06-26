from pathlib import Path
from time import time

HEARTBEAT_PATH = Path("/tmp/binbot_streaming.heartbeat")
MAX_HEARTBEAT_AGE_SECONDS = 120


def main() -> int:
    if not HEARTBEAT_PATH.exists():
        print(f"Missing heartbeat file: {HEARTBEAT_PATH}")
        return 1

    heartbeat_age = time() - HEARTBEAT_PATH.stat().st_mtime
    if heartbeat_age >= MAX_HEARTBEAT_AGE_SECONDS:
        print(
            "Stale heartbeat file: "
            f"{HEARTBEAT_PATH} age={heartbeat_age:.1f}s "
            f"max={MAX_HEARTBEAT_AGE_SECONDS}s"
        )
        return 1

    print(f"Streaming heartbeat healthy: age={heartbeat_age:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
