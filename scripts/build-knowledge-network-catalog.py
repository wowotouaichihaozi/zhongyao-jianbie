from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.showcase_network import write_course_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the compact document catalog used by the knowledge network.")
    parser.add_argument(
        "--index",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "course_knowledge_index.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    catalog = write_course_catalog(args.index.resolve(), args.output.resolve() if args.output else None)
    print(json.dumps({
        "documents": len(catalog["documents"]),
        "indexedChunks": catalog["indexedChunks"],
        "sourceIndexBytes": catalog["sourceIndexBytes"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
