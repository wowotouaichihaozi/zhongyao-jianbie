import json
import tempfile
import unittest
from pathlib import Path

from learning_agents import generate_learning_path
from scoring_evidence_suite import (
    build_effect_case,
    effect_scenarios,
    generate_tutor_evidence,
    resource_quality,
)


class ScoringEvidenceSuiteTests(unittest.TestCase):
    def test_tutor_evidence_accepts_api_data_shape(self):
        tutor = {
            "question": "Why does a GPIO output remain low?",
            "source": "grounded-test",
            "answer": "Check the peripheral clock, pin mode, output register, and observable voltage in that order.",
            "explanation": {
                "concept": "A GPIO output depends on both peripheral initialization and the output data path.",
                "steps": ["Check the clock", "Check the mode", "Verify the output"],
            },
            "socraticQuestions": ["Is the clock enabled?", "Which mode is selected?", "What does the register show?"],
            "feynmanTask": {
                "prompt": "Explain the GPIO data path in your own words.",
                "checklist": ["clock", "mode", "register"],
            },
            "hintLadder": [{"level": 1}, {"level": 2}, {"level": 3}],
            "practiceTasks": [{
                "question": "Diagnose a low GPIO output.",
                "answer": "Inspect clock, mode, and output register.",
                "explanation": "These checks follow the signal path.",
                "acceptanceCriteria": "Identify the first failing stage.",
            }],
            "multimodal": {
                "mermaid": {"code": "flowchart TD\nA[Clock] --> B[Mode] --> C[Output]"},
                "learningCard": {
                    "front": "GPIO remains low",
                    "back": "Check clock, mode, and register",
                    "keyPoints": ["clock", "mode", "register"],
                },
            },
            "references": [{"title": "GPIO course note", "source": "KB1"}],
            "qualityEvaluation": {"score": 95, "passed": True},
            "orchestration": {"rootAgent": "xiaozhi-companion-agent", "runId": "run-test"},
            "harness": {
                "skill": {"id": "learning.tutor.answer", "mcpTool": "learning.tutor.answer"},
                "modelRuntime": {"model": "xsparkx2agent"},
            },
        }
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            output_dir = Path(tempdir)
            case_dir = output_dir / "智能辅导案例"
            case_dir.mkdir(parents=True)
            (case_dir / "api-data-shape.json").write_text(
                json.dumps({"code": 0, "data": tutor}, ensure_ascii=False),
                encoding="utf-8",
            )
            evidence = generate_tutor_evidence(output_dir)

        self.assertEqual(evidence["caseCount"], 1)
        self.assertEqual(evidence["passed"], 1)
        self.assertEqual(evidence["cases"][0]["runId"], "run-test")
        self.assertEqual(evidence["cases"][0]["errors"], [])

    def test_tutor_evidence_reads_real_e2e_artifacts_by_task_id(self):
        tutor = {
            "question": "Why is UART output garbled?",
            "source": "grounded-test",
            "answer": "Compare clock, baud rate, and frame format.",
            "explanation": {"concept": "UART peers must agree on timing and framing.", "steps": ["clock", "baud", "frame"]},
            "socraticQuestions": ["Which clock is active?", "What baud is measured?", "Do frame formats match?"],
            "feynmanTask": {"prompt": "Explain UART framing.", "checklist": ["clock", "baud", "frame"]},
            "hintLadder": [{"level": 1}, {"level": 2}, {"level": 3}],
            "practiceTasks": [{"question": "Diagnose UART.", "answer": "Check timing.", "explanation": "Timing affects symbols.", "acceptanceCriteria": "Find the mismatch."}],
            "multimodal": {"mermaid": {"code": "flowchart TD\nA[Clock] --> B[Baud]"}, "learningCard": {"front": "UART", "back": "Match framing", "keyPoints": ["clock"]}},
            "references": [{"title": "UART note", "source": "KB1"}],
            "qualityEvaluation": {"score": 92, "passed": True},
        }
        result = {
            "tutor": tutor,
            "orchestration": {"rootAgent": "xiaozhi-companion-agent", "runId": "run-real"},
            "harness": {"skill": {"id": "learning.tutor.answer", "mcpTool": "learning.tutor.answer"}, "modelRuntime": {"model": "xsparkx2agent"}},
        }
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            output_dir = Path(tempdir)
            artifact_dir = output_dir / "真实讯飞接口结果"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "01-smart_tutor-task-1.json").write_text(
                json.dumps({"taskId": "task-1", "result": result}, ensure_ascii=False), encoding="utf-8"
            )
            report = {"cases": [{"skillId": "learning.tutor.answer", "taskId": "task-1"}]}
            evidence = generate_tutor_evidence(output_dir, report)

        self.assertEqual(evidence["caseCount"], 1)
        self.assertEqual(evidence["passed"], 1)
        self.assertEqual(evidence["cases"][0]["runId"], "run-real")

    def test_code_resource_quality_requires_code_and_grounding(self):
        quality = resource_quality(
            "code",
            {
                "title": "STM32 GPIO 画像薄弱点代码案例",
                "content": "[KB1]\n```c\n#include <stdint.h>\nvoid GPIO_Init(void) { }\nint main(void) { GPIO_Init(); }\n```\n" + ("验证步骤。" * 80),
            },
            review_passed=True,
            knowledge_source_count=2,
        )
        self.assertTrue(quality["passed"])
        self.assertGreaterEqual(quality["score"], 75)

    def test_effect_scenarios_have_complete_quantified_outputs(self):
        results = [build_effect_case(item) for item in effect_scenarios()]
        self.assertTrue(all(item["passed"] for item in results))
        self.assertEqual([item["assessment"]["achievementRate"] for item in results], sorted(item["assessment"]["achievementRate"] for item in results))
        self.assertEqual([item["assessment"]["masteryRate"] for item in results], sorted(item["assessment"]["masteryRate"] for item in results))

    def test_compatible_document_preference_changes_path_resource_mix(self):
        profile = {
            "_profileReportId": 9911,
            "chatStudentProfile": {
                "学习目标": ["完成 Linux 字符设备驱动实验"],
                "薄弱知识点": ["Linux 设备驱动模型", "内核中断上下文"],
                "学习风格/认知偏好": ["先读原理再验证", "结构化笔记"],
                "资源形式偏好": ["课程讲义", "技术文档"],
                "可投入时间": "每周 7 小时",
            },
        }
        result = generate_learning_path(
            {"profile": profile, "useLLM": False, "weekCount": 3, "totalWeeks": 3}
        )
        nodes = result["phases"][0]["nodes"]
        document_nodes = [item for item in nodes if item.get("resourceType") == "document"]
        self.assertTrue(document_nodes)
        self.assertTrue(all("讲义" in item.get("resourceSelectionReason", "") or "文档" in item.get("resourceSelectionReason", "") for item in document_nodes))


if __name__ == "__main__":
    unittest.main()
