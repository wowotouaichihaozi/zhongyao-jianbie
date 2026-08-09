"""Build a traceable 350-document supplement for the local course corpus.

Only official, openly licensed documentation repositories are used. Generated
text files retain their source URL and license so the lexical RAG index can cite
the material without losing provenance.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "rag文档" / "open-source"
WORK_DIR = PROJECT_ROOT / "tmp" / "knowledge-source-checkouts"

SOURCES = (
    {
        "key": "zephyr",
        "repository": "https://github.com/zephyrproject-rtos/zephyr.git",
        "sparse_path": "doc",
        "source_root": "doc",
        "license": "Apache-2.0",
        "label": "Zephyr Project 官方文档",
        "repository_name": "zephyrproject-rtos/zephyr",
        "limit": 1100,
        "extensions": {".rst", ".md"},
    },
    {
        "key": "espidf",
        "repository": "https://github.com/espressif/esp-idf.git",
        "repository_name": "espressif/esp-idf",
        "sparse_path": "docs/en",
        "source_root": "docs/en",
        "license": "Apache-2.0",
        "label": "ESP-IDF 官方文档",
        "limit": 1300,
        "extensions": {".rst", ".md"},
    },
    {
        "key": "nuttx",
        "repository": "https://github.com/apache/nuttx.git",
        "repository_name": "apache/nuttx",
        "sparse_path": "Documentation",
        "source_root": "Documentation",
        "license": "Apache-2.0",
        "label": "Apache NuttX 官方文档",
        "limit": 650,
        "extensions": {".rst", ".md", ".txt"},
    },
    {
        "key": "cmsis",
        "repository": "https://github.com/ARM-software/CMSIS_5.git",
        "repository_name": "ARM-software/CMSIS_5",
        "sparse_path": "CMSIS/DoxyGen",
        "source_root": "CMSIS/DoxyGen",
        "license": "Apache-2.0",
        "label": "Arm CMSIS 官方文档",
        "limit": 350,
        "extensions": {".md", ".txt", ".dox"},
    },
    {
        "key": "stm32cubef4",
        "repository": "https://github.com/STMicroelectronics/STM32CubeF4.git",
        "repository_name": "STMicroelectronics/STM32CubeF4",
        "sparse_path": "Projects",
        "source_root": "Projects",
        "license": "STMicroelectronics SLA0044",
        "label": "STM32CubeF4 官方示例说明",
        "limit": 600,
        "extensions": {".md", ".txt"},
    },
    {
        "key": "linux",
        "repository": "https://github.com/torvalds/linux.git",
        "repository_name": "torvalds/linux",
        "sparse_path": "Documentation",
        "source_root": "Documentation",
        "license": "GPL-2.0-only",
        "label": "Linux Kernel 官方文档",
        "limit": 1700,
        "extensions": {".rst", ".txt", ".md"},
    },
)

RELEVANCE_TERMS = (
    "arduino", "board", "build", "cortex", "debug", "device", "driver",
    "embedded", "gpio", "hardware", "i2c", "interrupt", "kernel", "memory",
    "network", "peripheral", "pwm", "rtos", "sensor", "serial", "spi", "thread",
    "timer", "uart", "usb", "zephyr", "开发", "单片机", "传感", "串口", "中断",
)


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def checkout(source: dict) -> Path:
    destination = WORK_DIR / source["key"]
    existing_source_root = destination / source["source_root"]
    if existing_source_root.exists():
        return existing_source_root
    last_error: Exception | None = None
    for attempt in range(1, 4):
        if destination.exists():
            shutil.rmtree(destination)
        try:
            run(
                "git", "-c", "http.version=HTTP/1.1", "-c", "core.longpaths=true",
                "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                source["repository"], str(destination),
            )
            run("git", "-c", "http.version=HTTP/1.1", "sparse-checkout", "set", source["sparse_path"], cwd=destination)
            return destination / source["source_root"]
        except subprocess.CalledProcessError as error:
            last_error = error
            if attempt < 3:
                time.sleep(attempt * 3)
    raise RuntimeError(f"unable to download {source['key']} after 3 attempts") from last_error


def normalize_document(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?m)^\s*\.\.[^\n]*::.*$", "", text)
    text = re.sub(r"(?m)^\s*:[\w-]+:\s*.*$", "", text)
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-=~^`:#*]{3,}\s*$", "", text)
    text = re.sub(r"`([^`<>]+?)\s*<[^>]+>`_?", r"\1", text)
    text = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def title_for(path: Path, content: str) -> str:
    for line in content.splitlines()[:20]:
        title = line.strip(" #*`:-\t")
        if len(title) >= 4:
            return title[:100]
    return path.stem.replace("_", " ")[:100]


def ranked_documents(root: Path, source: dict) -> list[Path]:
    candidates = [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in source["extensions"]
    ]

    def score(path: Path) -> tuple[int, str]:
        lowered = path.as_posix().lower()
        return (sum(term in lowered for term in RELEVANCE_TERMS), lowered)

    return sorted(candidates, key=score, reverse=True)


def split_source_document(content: str, target_size: int = 1200) -> list[str]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", content) if item.strip()]
    units: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= target_size:
            buffer = f"{buffer}\n\n{paragraph}".strip()
            continue
        if buffer:
            units.append(buffer)
        while len(paragraph) > target_size:
            units.append(paragraph[:target_size])
            paragraph = paragraph[target_size:]
        buffer = paragraph
    if buffer:
        units.append(buffer)
    return units or [content]


def write_documents(source: dict, source_root: Path) -> int:
    output_dir = CORPUS_DIR / source["key"]
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for path in ranked_documents(source_root, source):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        content = normalize_document(raw)
        if len(content) < 180:
            content = f"{path.stem}\n\n{content}".strip()
        relative = path.relative_to(source_root).as_posix()
        url = f"https://github.com/{source['repository_name']}/blob/main/{source['source_root']}/{relative}"
        units = split_source_document(content)
        for unit_index, unit in enumerate(units, start=1):
            if written >= source["limit"]:
                break
            written += 1
            title = title_for(path, unit)
            payload = (
                f"标题：{title}\n"
                f"来源：{source['label']}\n"
                f"许可：{source['license']}\n"
                f"原始链接：{url}\n"
                f"原始文档：{relative}\n"
                f"资料单元：{unit_index}/{len(units)}（按原文段落切分）\n"
                f"采集日期：{date.today().isoformat()}\n"
                f"主题：嵌入式系统、单片机、RTOS、接口与开发实践\n\n"
                f"{unit}\n"
            )
            (output_dir / f"{source['key'].upper()}_{written:04d}_{path.stem}.txt").write_text(payload, encoding="utf-8")
        if written >= source["limit"]:
            break
    if written < source["limit"]:
        raise RuntimeError(f"{source['key']} only produced {written} traceable knowledge units")
    return written


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in SOURCES:
        total += write_documents(source, checkout(source))
    if total < 5650:
        raise RuntimeError(f"expected at least 5650 traceable knowledge units, received {total}")
    print(f"Collected {total} traceable open-source documents into {CORPUS_DIR}")


if __name__ == "__main__":
    main()
