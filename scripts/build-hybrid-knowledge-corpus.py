from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_DIR = PROJECT_ROOT / "tmp" / "hybrid-knowledge-sources"
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "data" / "tcm_hybrid_corpus.db.gz"
DEFAULT_MANIFEST = PROJECT_ROOT / "backend" / "data" / "tcm_hybrid_corpus_manifest.json"
GRAPH_PATH = PROJECT_ROOT / "backend" / "data" / "tcm_graph_index.json"
CURATED_QA_PATH = PROJECT_ROOT / "backend" / "data" / "tcm_qa_pairs.json"

SOURCES = {
    "sylvan_qa": {
        "dataset": "SylvanL/Traditional-Chinese-Medicine-Dataset-SFT",
        "revision": "412f3ff8417bdf1d7d0e2157c4e5d2323a74b5e5",
        "filename": "SFT_medicalKnowledge_source2_99334.json",
        "cacheName": "sylvan-sft-source2.json",
        "sha256": "572394C4685FFB2082D91F0631A562A2B18EB77E78AE26F92E70B5FA7A1F9D7D",
        "license": "Apache-2.0",
        "kind": "qa",
    },
    "tcmchat_qa": {
        "dataset": "ZJUFanLab/TCMChat-dataset-600k",
        "revision": "c65f284fc43d7de94ecc83e58dac0db281d73295",
        "filename": "sft/train/knowledge.json",
        "cacheName": "tcmchat-knowledge.json",
        "sha256": "29C615226AE88F55538808ED2DAED5E3C794C2AD23BCC2A1B3755BE890945D40",
        "license": "Apache-2.0",
        "kind": "qa",
        "limit": 25000,
    },
    "cmmlu": {
        "dataset": "shuyuej/CMMLU-Traditional-Chinese-Medicine-Benchmark",
        "revision": "0008b9c567ed5c81f5c855312fe32abb07ea1742",
        "filename": "traditional_chinese_medicine.json",
        "cacheName": "cmmlu-tcm.json",
        "sha256": "CEB8E3DD3015259FC32CA9A70B964A22D5068C5AC2D5BAA13EBAC27CDBF4248C",
        "license": "Apache-2.0",
        "kind": "benchmark",
    },
    "sylvan_documents": {
        "dataset": "SylvanL/Traditional-Chinese-Medicine-Dataset-Pretrain",
        "revision": "fd01649d8e019ed2b002119e0fd74076c5f7b73d",
        "filename": "CPT_tcmKnowledge_source2_12889.json",
        "cacheName": "sylvan-pretrain-knowledge2.json",
        "sha256": "FD88C8DB6598E888319A6C79C3374B926420B64A359F708AD6A9005CB5B6051D",
        "license": "Apache-2.0",
        "kind": "document",
    },
}

TEXTBOOKS = (
    ("中医基础理论", "textbook-tcm-theory.txt", "2743E74F7D1CCAA17CB7C8911F332AFBBE0B057596394C342F3C37BCD851A6BA"),
    ("中药学", "textbook-herbology.txt", "F635D0C6F2373308CBD4C988C3C42D3F9C44A2844E3913DCD6144836F6D8F3B1"),
    ("方剂学", "textbook-formulas.txt", "7B7DEBA17B0CA712A6689C698DE768B6D4D88E1B0FDAB3E1B48B1C7475D78750"),
    ("伤寒论", "textbook-shanghan.txt", "9351332B537C8C00125699CEAB2944A7DD6F9BAC510B3320AF5FD4CCCD0E86BD"),
)
TCMCHAT_REVISION = "c65f284fc43d7de94ecc83e58dac0db281d73295"
TCMCHAT_DATASET = "ZJUFanLab/TCMChat-dataset-600k"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the immutable hybrid TCM retrieval corpus.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def clean_text(value: object) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact(value: object) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", clean_text(value).lower())


def tokens(value: object) -> list[str]:
    text = clean_text(value).lower()
    result = re.findall(r"[a-z][a-z0-9_+\-]{1,}|[0-9]+(?:\.[0-9]+)?", text)
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        result.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
        if len(sequence) <= 12:
            result.append(sequence)
    return list(dict.fromkeys(result))


def search_terms(*values: object, max_chars: int = 900) -> str:
    return " ".join(tokens(" ".join(clean_text(value) for value in values)[:max_chars]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def source_url(dataset: str, revision: str, filename: str) -> str:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in filename.split("/"))
    return f"https://huggingface.co/datasets/{dataset}/resolve/{revision}/{encoded}"


def ensure_source(cache_dir: Path, config: dict[str, Any]) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / config["cacheName"]
    if not target.exists():
        urllib.request.urlretrieve(
            source_url(config["dataset"], config["revision"], config["filename"]),
            target,
        )
    actual = sha256(target)
    if actual != config["sha256"]:
        raise RuntimeError(f"Source checksum mismatch for {target.name}: {actual}")
    return target


def deterministic_subset(items: list[dict[str, Any]], limit: int, key_builder) -> list[dict[str, Any]]:
    if len(items) <= limit:
        return items
    ranked = sorted(
        items,
        key=lambda item: hashlib.sha1(key_builder(item).encode("utf-8", errors="ignore")).hexdigest(),
    )
    return ranked[:limit]


def split_text(text: str, target_size: int = 900, overlap: int = 120) -> list[str]:
    clean = clean_text(text)
    if not clean:
        return []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", clean) if item.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= target_size:
            buffer = f"{buffer}\n\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append(buffer)
        if len(paragraph) <= target_size:
            buffer = paragraph
            continue
        start = 0
        while start < len(paragraph):
            end = min(len(paragraph), start + target_size)
            chunks.append(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = max(start + 1, end - overlap)
        buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def valid_qa(question: str, answer: str) -> bool:
    if not 4 <= len(question) <= 320 or not 8 <= len(answer) <= 4000:
        return False
    if len(compact(question)) < 4 or len(compact(answer)) < 8:
        return False
    return True


def qa_record(
    item_id: str,
    question: str,
    answer: str,
    *,
    dataset: str,
    source: str,
    revision: str,
    license_name: str,
    tags: Iterable[str] = (),
) -> dict[str, str] | None:
    question = clean_text(question)
    answer = clean_text(answer)
    if not valid_qa(question, answer):
        return None
    tag_text = " ".join(clean_text(tag) for tag in tags if clean_text(tag))[:500]
    return {
        "id": item_id,
        "dataset": dataset,
        "source": source,
        "revision": revision,
        "license": license_name,
        "question": question,
        "answer": answer,
        "tags": tag_text,
        "safety": "educational_only;not_for_clinical_diagnosis_or_prescription",
    }


def load_qa(cache_dir: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    records: list[dict[str, str]] = []
    counts: dict[str, int] = {}

    curated = json.loads(CURATED_QA_PATH.read_text(encoding="utf-8"))
    for item in curated.get("qaPairs", []):
        record = qa_record(
            item.get("id") or "",
            item.get("question") or "",
            item.get("answer") or "",
            dataset="岐黄智境内置中医 QA",
            source="QA_中医知识问答.txt",
            revision=curated.get("version") or "1.0",
            license_name="Project-authored",
            tags=item.get("tags") or [],
        )
        if record:
            records.append(record)
    counts["projectCurated"] = len(records)

    sylvan_config = SOURCES["sylvan_qa"]
    sylvan_path = ensure_source(cache_dir, sylvan_config)
    sylvan_items = json.loads(sylvan_path.read_text(encoding="utf-8"))
    before = len(records)
    for index, item in enumerate(sylvan_items, start=1):
        instruction = clean_text(item.get("instruction"))
        input_text = clean_text(item.get("input"))
        question = input_text or instruction
        if instruction and input_text and instruction not in {"问答", "请回答", ""}:
            question = f"{instruction}\n{input_text}"
        record = qa_record(
            f"SYL-SFT2-{index:06d}",
            question,
            item.get("output") or "",
            dataset=sylvan_config["dataset"],
            source=sylvan_config["filename"],
            revision=sylvan_config["revision"],
            license_name=sylvan_config["license"],
            tags=("中医知识", "术语", "方药", "针灸"),
        )
        if record:
            records.append(record)
    counts["sylvanSft"] = len(records) - before

    tcmchat_config = SOURCES["tcmchat_qa"]
    tcmchat_path = ensure_source(cache_dir, tcmchat_config)
    tcmchat_items = json.loads(tcmchat_path.read_text(encoding="utf-8"))
    tcmchat_items = deterministic_subset(
        tcmchat_items,
        int(tcmchat_config["limit"]),
        lambda item: f"{item.get('instruction', '')}\n{item.get('input', '')}\n{item.get('output', '')}",
    )
    before = len(records)
    for index, item in enumerate(tcmchat_items, start=1):
        question = clean_text(item.get("input")) or clean_text(item.get("instruction"))
        record = qa_record(
            f"TCMCHAT-K-{index:06d}",
            question,
            item.get("output") or "",
            dataset=tcmchat_config["dataset"],
            source=tcmchat_config["filename"],
            revision=tcmchat_config["revision"],
            license_name=tcmchat_config["license"],
            tags=(clean_text(item.get("instruction")), "中医知识问答"),
        )
        if record:
            records.append(record)
    counts["tcmChatKnowledge"] = len(records) - before

    cmmlu_config = SOURCES["cmmlu"]
    cmmlu_path = ensure_source(cache_dir, cmmlu_config)
    cmmlu_items = json.loads(cmmlu_path.read_text(encoding="utf-8"))
    before = len(records)
    for index, item in enumerate(cmmlu_items, start=1):
        options = "；".join(f"{label}. {clean_text(item.get(label))}" for label in "ABCD")
        label = clean_text(item.get("label")).upper()
        record = qa_record(
            f"CMMLU-TCM-{index:04d}",
            f"{clean_text(item.get('question'))}\n{options}",
            f"正确答案：{label}. {clean_text(item.get(label))}",
            dataset=cmmlu_config["dataset"],
            source=cmmlu_config["filename"],
            revision=cmmlu_config["revision"],
            license_name=cmmlu_config["license"],
            tags=("中医考试", "选择题"),
        )
        if record:
            records.append(record)
    counts["cmmluBenchmark"] = len(records) - before

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    before = len(records)
    for item in graph.get("nodes", [])[1:]:
        title = clean_text(item.get("title"))
        answer = clean_text(item.get("explanation") or item.get("summary"))
        record = qa_record(
            f"GRAPH-QA-{item.get('id')}",
            f"请解释“{title}”的核心知识与学习边界。",
            answer,
            dataset="岐黄智境中医药知识图谱",
            source="tcm-knowledge-network.v1.2-substantive.json",
            revision=graph.get("version") or "1.2",
            license_name="Project-provided dataset",
            tags=(item.get("domain") or "", *(item.get("tags") or []), *(item.get("path") or [])),
        )
        if record:
            records.append(record)
    counts["graphDerived"] = len(records) - before

    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        fingerprint = hashlib.sha256(compact(record["question"]).encode("utf-8")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduplicated.append(record)
    counts["deduplicatedTotal"] = len(deduplicated)
    counts["duplicatesRemoved"] = len(records) - len(deduplicated)
    return deduplicated, counts


def document_record(
    item_id: str,
    title: str,
    content: str,
    *,
    dataset: str,
    source: str,
    revision: str,
    license_name: str,
    chunk_index: int,
    tags: Iterable[str] = (),
) -> dict[str, str | int] | None:
    content = clean_text(content)
    if len(compact(content)) < 40:
        return None
    title = clean_text(title)[:240] or source
    tag_text = " ".join(clean_text(tag) for tag in tags if clean_text(tag))[:500]
    return {
        "id": item_id,
        "dataset": dataset,
        "source": source,
        "revision": revision,
        "license": license_name,
        "title": title,
        "content": content[:4000],
        "tags": tag_text,
        "chunkIndex": chunk_index,
        "safety": "educational_only;not_for_clinical_diagnosis_or_prescription",
    }


def load_documents(cache_dir: Path) -> tuple[list[dict[str, str | int]], dict[str, int]]:
    records: list[dict[str, str | int]] = []
    counts: dict[str, int] = {}
    sylvan_config = SOURCES["sylvan_documents"]
    sylvan_path = ensure_source(cache_dir, sylvan_config)
    sylvan_items = json.loads(sylvan_path.read_text(encoding="utf-8"))
    if sylvan_config.get("limit"):
        sylvan_items = deterministic_subset(
            sylvan_items,
            int(sylvan_config["limit"]),
            lambda item: clean_text(item.get("text")),
        )
    before = len(records)
    for item_index, item in enumerate(sylvan_items, start=1):
        text = clean_text(item.get("text"))
        title_match = re.search(
            r"(?:中文名称|中药材|方剂|证候|药膳食疗|名称|方名|病名|药名)[:：]\s*([^\n]{2,80})",
            text,
        )
        title = clean_text(title_match.group(1)) if title_match else f"中医术语与方药资料 {item_index}"
        for chunk_index, chunk in enumerate(split_text(text), start=1):
            record = document_record(
                f"SYL-CPT2-{item_index:05d}-{chunk_index:02d}",
                title,
                chunk,
                dataset=sylvan_config["dataset"],
                source=sylvan_config["filename"],
                revision=sylvan_config["revision"],
                license_name=sylvan_config["license"],
                chunk_index=chunk_index,
                tags=("中医术语", "方药", "针灸", "规范知识"),
            )
            if record:
                records.append(record)
    counts["sylvanKnowledgeChunks"] = len(records) - before

    for title, cache_name, expected_hash in TEXTBOOKS:
        config = {
            "dataset": TCMCHAT_DATASET,
            "revision": TCMCHAT_REVISION,
            "filename": f"pretrain/train/books/textbook/{title}.txt",
            "cacheName": cache_name,
            "sha256": expected_hash,
        }
        path = ensure_source(cache_dir, config)
        before = len(records)
        for chunk_index, chunk in enumerate(split_text(path.read_text(encoding="utf-8")), start=1):
            record = document_record(
                f"TCMCHAT-TEXT-{hashlib.sha1(title.encode('utf-8')).hexdigest()[:8]}-{chunk_index:05d}",
                title,
                chunk,
                dataset=TCMCHAT_DATASET,
                source=config["filename"],
                revision=TCMCHAT_REVISION,
                license_name="Apache-2.0",
                chunk_index=chunk_index,
                tags=("中医教材", title),
            )
            if record:
                records.append(record)
        counts[f"textbook:{title}"] = len(records) - before

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    before = len(records)
    for item in graph.get("nodes", [])[1:]:
        record = document_record(
            f"GRAPH-DOC-{item.get('id')}",
            item.get("title") or "中医知识图谱节点",
            item.get("explanation") or item.get("summary") or "",
            dataset="岐黄智境中医药知识图谱",
            source="tcm-knowledge-network.v1.2-substantive.json",
            revision=graph.get("version") or "1.2",
            license_name="Project-provided dataset",
            chunk_index=1,
            tags=(item.get("domain") or "", *(item.get("tags") or []), *(item.get("path") or [])),
        )
        if record:
            records.append(record)
    counts["graphDerivedChunks"] = len(records) - before

    deduplicated: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for record in records:
        fingerprint = hashlib.sha256(compact(record["content"]).encode("utf-8")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduplicated.append(record)
    counts["deduplicatedTotal"] = len(deduplicated)
    counts["duplicatesRemoved"] = len(records) - len(deduplicated)
    return deduplicated, counts


def build_database(output: Path, qa_records: list[dict[str, str]], documents: list[dict[str, Any]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    conn = sqlite3.connect(temporary)
    try:
        conn.executescript(
            """
            PRAGMA journal_mode = OFF;
            PRAGMA synchronous = OFF;
            PRAGMA temp_store = MEMORY;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE qa_pairs (
                id TEXT PRIMARY KEY, dataset TEXT NOT NULL, source TEXT NOT NULL,
                revision TEXT NOT NULL, license TEXT NOT NULL, question TEXT NOT NULL,
                answer BLOB NOT NULL, tags TEXT NOT NULL, safety TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE qa_fts USING fts5(
                search_terms, content='', detail=none, columnsize=0, tokenize='unicode61'
            );
            CREATE TABLE document_chunks (
                id TEXT PRIMARY KEY, dataset TEXT NOT NULL, source TEXT NOT NULL,
                revision TEXT NOT NULL, license TEXT NOT NULL, title TEXT NOT NULL,
                content BLOB NOT NULL, tags TEXT NOT NULL, chunk_index INTEGER NOT NULL,
                safety TEXT NOT NULL
            );
            CREATE INDEX document_chunks_title_idx ON document_chunks(title);
            CREATE VIRTUAL TABLE document_fts USING fts5(
                search_terms, content='', detail=none, columnsize=0, tokenize='unicode61'
            );
            """
        )
        conn.executemany(
            "INSERT INTO qa_pairs VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    record["id"], record["dataset"], record["source"], record["revision"],
                    record["license"], record["question"],
                    sqlite3.Binary(zlib.compress(record["answer"].encode("utf-8"), level=9)),
                    record["tags"], record["safety"],
                )
                for record in qa_records
            ],
        )
        conn.executemany(
            "INSERT INTO qa_fts(rowid, search_terms) VALUES (?, ?)",
            [
                (index, search_terms(record["question"], record["tags"], max_chars=500))
                for index, record in enumerate(qa_records, start=1)
            ],
        )
        conn.executemany(
            "INSERT INTO document_chunks VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    record["id"], record["dataset"], record["source"], record["revision"],
                    record["license"], record["title"],
                    sqlite3.Binary(zlib.compress(str(record["content"]).encode("utf-8"), level=9)),
                    record["tags"], record["chunkIndex"], record["safety"],
                )
                for record in documents
            ],
        )
        conn.executemany(
            "INSERT INTO document_fts(rowid, search_terms) VALUES (?, ?)",
            [
                (
                    index,
                    search_terms(record["title"], record["tags"], str(record["content"])[:360], max_chars=650),
                )
                for index, record in enumerate(documents, start=1)
            ],
        )
        metadata = {
            "schemaVersion": "hybrid-corpus-v1",
            "qaPairs": str(len(qa_records)),
            "documentChunks": str(len(documents)),
            "clinicalUse": "false",
        }
        conn.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()
    finally:
        conn.close()
    os.replace(temporary, output)


def compress_database(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with source.open("rb") as source_handle, temporary.open("wb") as raw_handle:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw_handle,
            compresslevel=9,
            mtime=0,
        ) as compressed:
            for block in iter(lambda: source_handle.read(1024 * 1024), b""):
                compressed.write(block)
    os.replace(temporary, output)


def main() -> int:
    args = parse_args()
    qa_records, qa_counts = load_qa(args.cache_dir)
    documents, document_counts = load_documents(args.cache_dir)
    raw_database = args.cache_dir / "tcm_hybrid_corpus.db"
    build_database(raw_database, qa_records, documents)
    compress_database(raw_database, args.output)
    source_manifest = []
    for config in SOURCES.values():
        path = args.cache_dir / config["cacheName"]
        source_manifest.append(
            {
                "dataset": config["dataset"],
                "revision": config["revision"],
                "file": config["filename"],
                "license": config["license"],
                "sha256": sha256(path),
                "kind": config["kind"],
                "includedLimit": config.get("limit"),
            }
        )
    source_manifest.append(
        {
            "dataset": TCMCHAT_DATASET,
            "revision": TCMCHAT_REVISION,
            "files": [f"pretrain/train/books/textbook/{title}.txt" for title, _, _ in TEXTBOOKS],
            "license": "Apache-2.0",
            "kind": "document",
        }
    )
    manifest = {
        "schemaVersion": "hybrid-corpus-v1",
        "purpose": "中医学习混合检索；仅用于教育，不用于临床诊断、处方或治疗决策。",
        "qa": qa_counts,
        "documents": document_counts,
        "database": {
            "path": args.output.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": args.output.stat().st_size,
            "sha256": sha256(args.output),
            "uncompressedBytes": raw_database.stat().st_size,
            "uncompressedSha256": sha256(raw_database),
        },
        "sources": source_manifest,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
