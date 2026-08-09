from __future__ import annotations

import unittest

import app as app_module


class XiaoZhiQuestionPayloadTests(unittest.TestCase):
    def test_requested_count_is_distributed_exactly(self) -> None:
        counts = app_module.xiaozhi_distribute_question_type_counts(
            ["单选题", "判断题", "填空题", "简答题"],
            10,
        )

        self.assertEqual(counts, {"单选题": 3, "判断题": 3, "填空题": 2, "简答题": 2})
        self.assertEqual(sum(counts.values()), 10)

    def test_small_count_does_not_create_zero_count_types(self) -> None:
        counts = app_module.xiaozhi_distribute_question_type_counts(
            ["单选题", "判断题", "填空题", "简答题"],
            2,
        )

        self.assertEqual(counts, {"单选题": 1, "判断题": 1})
        self.assertEqual(sum(counts.values()), 2)


if __name__ == "__main__":
    unittest.main()
