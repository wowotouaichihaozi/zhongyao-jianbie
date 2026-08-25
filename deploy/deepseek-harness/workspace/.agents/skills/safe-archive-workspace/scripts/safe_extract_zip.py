#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile


MAX_ENTRIES = 2_000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
COPY_CHUNK_BYTES = 1024 * 1024


def fail(message: str) -> None:
    raise ValueError(message)


def normalized_member(name: str) -> PurePosixPath:
    if "\x00" in name:
        fail("archive member contains a NUL byte")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        fail(f"unsafe archive path: {name!r}")
    if path.parts and ":" in path.parts[0]:
        fail(f"drive-qualified archive path: {name!r}")
    return path


def validate_entry(info: zipfile.ZipInfo) -> PurePosixPath:
    if info.flag_bits & 0x1:
        fail(f"encrypted archive entry is not allowed: {info.filename!r}")
    target = normalized_member(info.filename)
    mode = (info.external_attr >> 16) & 0o170000
    if stat.S_ISLNK(mode):
        fail(f"symbolic link is not allowed: {info.filename!r}")
    if mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        fail(f"special file is not allowed: {info.filename!r}")
    if info.file_size > MAX_FILE_BYTES:
        fail(f"archive entry exceeds 128 MiB: {info.filename!r}")
    compressed = max(1, info.compress_size)
    if info.file_size > 1024 * 1024 and info.file_size / compressed > MAX_COMPRESSION_RATIO:
        fail(f"suspicious compression ratio: {info.filename!r}")
    return target


def ensure_within(root: Path, target: Path) -> None:
    if os.path.commonpath((str(root), str(target))) != str(root):
        fail("archive target escaped the extraction directory")


def extract(archive: Path, destination: Path) -> dict[str, int | bool]:
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        fail("input must be an existing ZIP file")
    if destination.exists() and any(destination.iterdir()):
        fail("destination directory must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) > MAX_ENTRIES:
            fail("archive contains more than 2,000 entries")

        planned: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
        seen: set[str] = set()
        total = 0
        for info in infos:
            member = validate_entry(info)
            key = member.as_posix().rstrip("/")
            if key in seen:
                fail(f"duplicate archive target: {key!r}")
            seen.add(key)
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                fail("archive expands beyond 512 MiB")
            planned.append((info, member))

        written = 0
        for info, member in planned:
            target = (root / Path(*member.parts)).resolve()
            ensure_within(root, target)
            if info.is_dir() or info.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("xb") as output:
                copied = 0
                while True:
                    chunk = source.read(COPY_CHUNK_BYTES)
                    if not chunk:
                        break
                    copied += len(chunk)
                    written += len(chunk)
                    if copied > info.file_size or copied > MAX_FILE_BYTES or written > MAX_TOTAL_BYTES:
                        fail("archive exceeded its declared safe expansion limits")
                    output.write(chunk)
                if copied != info.file_size:
                    fail(f"archive entry size mismatch: {info.filename!r}")

    return {"ok": True, "entries": len(planned), "totalBytes": written}


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"ok": False, "error": "usage: safe_extract_zip.py ARCHIVE DESTINATION"}))
        return 2
    try:
        result = extract(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(json.dumps({"ok": False, "error": str(error)}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
