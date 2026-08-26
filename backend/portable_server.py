"""Windows portable entry point for the unified learner and admin service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# The official Windows embeddable runtime isolates sys.path from the script
# directory, so register the backend directory before importing local modules.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from waitress import serve

from app import app, start_learning_path_resource_recovery


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def main() -> None:
    start_learning_path_resource_recovery()

    host = os.getenv("PORTABLE_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = _bounded_int("PORT", 3000, 1, 65535)
    threads = _bounded_int("PORTABLE_THREADS", 8, 4, 32)
    serve(app, host=host, port=port, threads=threads, channel_timeout=120)


if __name__ == "__main__":
    main()
