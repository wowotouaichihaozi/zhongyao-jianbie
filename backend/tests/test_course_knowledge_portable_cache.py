import json
import tempfile
import unittest
from pathlib import Path

from backend.course_knowledge import CACHE_VERSION, CourseKnowledgeBase


class PortableCourseKnowledgeCacheTests(unittest.TestCase):
    def test_missing_raw_corpus_does_not_overwrite_packaged_index(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            root = Path(tempdir)
            corpus = root / "missing-corpus"
            cache = root / "course-index.json"
            payload = {
                "version": CACHE_VERSION,
                "signatures": {"source.txt": "source.txt:100:1"},
                "pdfSignatures": {},
                "chunks": [{
                    "chunk_id": "source.txt#section-1",
                    "source": "source.txt",
                    "title": "Portable source",
                    "content": "FreeRTOS portable indexed knowledge",
                    "page": None,
                    "section": 1,
                }],
            }
            cache.write_text(json.dumps(payload), encoding="utf-8")
            before = cache.read_bytes()

            knowledge = CourseKnowledgeBase(corpus_dir=corpus, cache_path=cache)
            result = knowledge.retrieve("FreeRTOS", top_k=1)

            self.assertTrue(result["grounded"])
            self.assertEqual(result["stats"]["indexedChunks"], 1)
            self.assertEqual(cache.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
