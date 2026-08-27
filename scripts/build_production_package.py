from __future__ import annotations

import argparse
import hashlib
import re
import tarfile
from datetime import datetime
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = PROJECT_ROOT / ".deploy_bundle"
KNOWLEDGE_DIR_NAME = "rag\u6587\u6863"

REQUIRED_FILES = (
    "backend/app.py",
    "backend/requirements.txt",
    "backend/data/course_knowledge_index.json",
    "backend/data/tcm_qa_pairs.json",
    "backend/data/tcm_graph_index.json",
    "backend/data/tcm_hybrid_corpus.db.gz",
    "backend/data/tcm_hybrid_corpus_manifest.json",
    "frontend/dist/index.html",
    "mobile/dist/index.html",
    "admin/dist/index.html",
    "ppth5/backend/main.py",
    "ppth5/backend/requirements.txt",
    "ppth5/dist-web/index.html",
    "deploy.sh",
    "deploy-prod.sh",
)

ROOT_FILES = (
    "deploy.sh",
    "deploy-prod.sh",
    "README.md",
    "SCORING_MATRIX.md",
    "THIRD_PARTY_NOTICES.md",
)

FORBIDDEN_ARCHIVE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(^|/)\.env$",
        r"\.key$",
        r"(^|/)auth\.sqlite3$",
        r"(^|/)profile_workflow.*\.sqlite$",
        r"(^|/)question_generator\.sqlite3$",
        r"(^|/)(venv|node_modules|generated|profile_portraits)(/|$)",
        r"\.(pyc|pyo|log)$",
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the production runtime archive.")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def relative_name(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def include_backend(path: Path) -> bool:
    name = relative_name(path)
    parts = PurePosixPath(name).parts
    if any(part in {"venv", "generated", "__pycache__", ".pytest_cache"} for part in parts):
        return False
    if path.name == ".env" or path.suffix.lower() in {".pyc", ".pyo", ".log"}:
        return False
    if name.startswith("backend/data/"):
        return name in {
            "backend/data/course_knowledge_index.json",
            "backend/data/tcm_qa_pairs.json",
            "backend/data/tcm_graph_index.json",
            "backend/data/tcm_hybrid_corpus.db.gz",
            "backend/data/tcm_hybrid_corpus_manifest.json",
        }
    return True


def include_ppt_backend(path: Path) -> bool:
    parts = PurePosixPath(relative_name(path)).parts
    if any(part in {".venv", "__pycache__", ".pytest_cache"} for part in parts):
        return False
    if path.name == ".env" or path.suffix.lower() in {".pyc", ".pyo", ".log"}:
        return False
    return True


def include_frontend_dist(path: Path) -> bool:
    parts = PurePosixPath(relative_name(path)).parts
    return "generated" not in parts


def iter_tree(relative_root: str, predicate=None):
    root = PROJECT_ROOT / relative_root
    if not root.is_dir():
        raise FileNotFoundError(f"Required release directory is missing: {relative_root}")
    for path in sorted(root.rglob("*")):
        if path.is_file() and (predicate is None or predicate(path)):
            yield path


def collect_release_files() -> list[Path]:
    files: set[Path] = set()
    files.update(iter_tree("backend", include_backend))
    files.update(iter_tree("frontend/dist", include_frontend_dist))
    files.update(iter_tree("mobile/dist", include_frontend_dist))
    files.update(iter_tree("admin/dist"))
    files.update(iter_tree("ppth5/backend", include_ppt_backend))
    files.update(iter_tree("ppth5/dist-web"))
    files.update(iter_tree("ppth5/resources"))
    files.update(iter_tree(KNOWLEDGE_DIR_NAME))

    docs = PROJECT_ROOT / "docs"
    if docs.is_dir():
        files.update(iter_tree("docs"))

    for relative_path in ROOT_FILES:
        path = PROJECT_ROOT / relative_path
        if path.is_file():
            files.add(path)

    return sorted(files, key=relative_name)


def normalized_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = 0o755 if info.name in {"deploy.sh", "deploy-prod.sh"} else 0o644
    return info


def validate_archive(output_path: Path, expected_knowledge_files: int) -> tuple[int, int]:
    with tarfile.open(output_path, "r:gz") as archive:
        names = [member.name for member in archive.getmembers() if member.isfile()]

    for name in names:
        if any(pattern.search(name) for pattern in FORBIDDEN_ARCHIVE_PATTERNS):
            raise RuntimeError(f"Forbidden runtime or secret-bearing file in archive: {name}")

    for required_file in REQUIRED_FILES:
        if required_file not in names:
            raise RuntimeError(f"Required file is absent from release archive: {required_file}")

    knowledge_prefix = f"{KNOWLEDGE_DIR_NAME}/"
    archived_knowledge_files = sum(name.startswith(knowledge_prefix) for name in names)
    if archived_knowledge_files != expected_knowledge_files:
        raise RuntimeError(
            "Knowledge corpus mismatch: "
            f"expected {expected_knowledge_files} files, archived {archived_knowledge_files}"
        )

    return len(names), archived_knowledge_files


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    args = parse_args()
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output
    if output_path is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = RELEASE_DIR / f"feishengwangying-{stamp}-production.tar.gz"
    output_path = output_path.expanduser().resolve()

    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite an existing archive: {output_path}")

    for relative_path in REQUIRED_FILES:
        if not (PROJECT_ROOT / relative_path).is_file():
            raise FileNotFoundError(f"Required release file is missing: {relative_path}")

    release_files = collect_release_files()
    knowledge_root = PROJECT_ROOT / KNOWLEDGE_DIR_NAME
    expected_knowledge_files = sum(path.is_file() for path in knowledge_root.rglob("*"))

    try:
        with tarfile.open(output_path, "w:gz", compresslevel=6) as archive:
            for path in release_files:
                archive.add(
                    path,
                    arcname=relative_name(path),
                    recursive=False,
                    filter=normalized_tar_info,
                )

        file_count, knowledge_file_count = validate_archive(
            output_path,
            expected_knowledge_files,
        )
        digest = sha256_file(output_path)
        checksum_path = Path(f"{output_path}.sha256")
        checksum_path.write_text(f"{digest}  {output_path.name}\n", encoding="ascii")

        print(f"ARCHIVE={output_path}")
        print(f"BYTES={output_path.stat().st_size}")
        print(f"FILES={file_count}")
        print(f"KNOWLEDGE_FILES={knowledge_file_count}")
        print(f"SHA256={digest}")
        print(f"CHECKSUM_FILE={checksum_path}")
        return 0
    except Exception:
        output_path.unlink(missing_ok=True)
        Path(f"{output_path}.sha256").unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
