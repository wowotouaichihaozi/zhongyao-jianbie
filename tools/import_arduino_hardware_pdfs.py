"""Import relevant Arduino hardware PDFs into the course knowledge corpus.

Only downloadable board documentation is imported: schematics, pinouts,
datasheets, manuals and hardware design notes. Certification files are excluded.
Each copied PDF is recorded in a provenance manifest with its official source URL.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT / "tmp" / "knowledge-source-checkouts" / "arduino" / "content"
OUTPUT_DIR = PROJECT_ROOT / "rag文档" / "arduino-official-hardware"
MANIFEST = OUTPUT_DIR / "SOURCE_MANIFEST.md"


def eligible_pdfs() -> list[Path]:
    documents = []
    for path in SOURCE_ROOT.rglob("*.pdf"):
        relative = path.relative_to(SOURCE_ROOT).as_posix()
        if "/downloads/" not in f"/{relative}" or "/certifications/" in f"/{relative}":
            continue
        if path.stat().st_size < 4096:
            continue
        documents.append(path)
    return sorted(documents, key=lambda item: item.as_posix().lower())


def main() -> None:
    if not SOURCE_ROOT.exists():
        raise RuntimeError(f"Arduino documentation checkout was not found: {SOURCE_ROOT}")
    documents = eligible_pdfs()
    if not documents:
        raise RuntimeError("No eligible Arduino hardware PDFs were found")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = [
        "# Arduino Official Hardware PDF Sources",
        "",
        "Scope: board pinouts, schematics, datasheets, manuals and hardware design downloads.",
        "Excluded: certification and compliance documents.",
        "Source repository: https://github.com/arduino/docs-content",
        "License: CC BY-SA 4.0, subject to the upstream repository terms.",
        f"Imported: {date.today().isoformat()}",
        "",
        "| File | Original path | Source URL | Size (bytes) |",
        "| --- | --- | --- | ---: |",
    ]
    total_bytes = 0
    for index, source in enumerate(documents, start=1):
        relative = source.relative_to(SOURCE_ROOT).as_posix()
        filename = f"ARDUINO_HW_{index:04d}_{source.name}"
        destination = OUTPUT_DIR / filename
        shutil.copy2(source, destination)
        total_bytes += destination.stat().st_size
        url = f"https://github.com/arduino/docs-content/blob/main/content/{relative}"
        artifact_name = source.stem.lower()
        artifact_type = (
            "原理图" if "schematic" in artifact_name or "schem" in artifact_name
            else "引脚图" if "pinout" in artifact_name
            else "数据手册" if "datasheet" in artifact_name
            else "硬件设计资料"
        )
        (OUTPUT_DIR / f"ARDUINO_HW_{index:04d}_CATALOG.txt").write_text(
            "\n".join(
                [
                    f"标题：Arduino {artifact_type} - {source.stem}",
                    "来源：Arduino 官方硬件资料",
                    "许可：CC BY-SA 4.0，具体以原始仓库条款为准",
                    f"原始链接：{url}",
                    f"原始文档：{relative}",
                    f"本地 PDF：{filename}",
                    f"资料类型：{artifact_type}",
                    "说明：本条目仅用于定位官方原始 PDF；具体引脚、电气参数、接线和版本信息必须以 PDF 原文为准。",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        manifest.append(f"| {filename} | {relative} | {url} | {destination.stat().st_size} |")

    MANIFEST.write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Imported {len(documents)} Arduino hardware PDFs ({total_bytes / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
