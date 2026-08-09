from __future__ import annotations

import unittest
from unittest.mock import patch

import learning_tutor
from multi_agent_runtime import review_specialist_output


def valid_tutor_raw() -> dict:
    return {
        "answer": "GPIO 输入模式的关键是先确认引脚配置，再观察输入数据寄存器中的电平变化。",
        "diagnosis": {
            "learnerStage": "STM32 基础阶段",
            "likelyMisconception": "把上拉输入与输出高电平混淆",
            "profileEvidence": ["当前薄弱点为 GPIO"],
        },
        "explanation": {
            "concept": "输入模式由配置寄存器决定，读取值来自输入数据寄存器。",
            "analogy": "引脚像传感器入口，配置决定入口如何解释外部电平。",
            "steps": ["确认端口时钟", "配置输入模式", "读取并验证电平"],
        },
        "socraticQuestions": [
            {"question": "为什么输入前要开启端口时钟？", "intent": "检查前置条件", "expectedKeyPoints": "时钟门控", "revealCondition": "先回答"},
            {"question": "悬空输入可能出现什么现象？", "intent": "理解稳定性", "expectedKeyPoints": "不确定电平", "revealCondition": "完成第一问"},
            {"question": "如何用最小实验验证读取结果？", "intent": "迁移验证", "expectedKeyPoints": "改变输入并观察", "revealCondition": "完成第二问"},
        ],
        "feynmanTask": {
            "prompt": "向同学解释输入模式和输入数据寄存器的关系。",
            "audience": "嵌入式初学者",
            "checklist": ["说清配置", "说清读取", "给出实验"],
        },
        "hintLadder": [
            {"level": 1, "title": "方向", "hint": "先看时钟和模式", "revealWhen": "无法开始"},
            {"level": 2, "title": "关键", "hint": "区分配置与数据寄存器", "revealWhen": "概念混淆"},
            {"level": 3, "title": "接近答案", "hint": "用按键改变输入电平", "revealWhen": "仍无法验证"},
        ],
        "practiceTasks": [
            {
                "type": "实验诊断",
                "question": "设计按键输入验证步骤。",
                "answer": "开启时钟、配置输入、循环读取、改变按键状态并记录。",
                "explanation": "用可观察电平变化验证配置与读取链路。",
                "difficulty": "medium",
                "acceptanceCriteria": "能记录至少两种输入状态及对应读取值",
            }
        ],
        "multimodal": {
            "mermaid": {"type": "flowchart", "code": "flowchart TD\nA[开启时钟] --> B[配置输入]\nB --> C[读取电平]"},
            "learningCard": {
                "title": "GPIO 输入",
                "front": "配置和读取分别负责什么？",
                "back": "配置决定模式，输入数据寄存器反映电平。",
                "keyPoints": ["时钟", "模式", "读取", "验证"],
            },
            "narrationScript": ["先确认时钟。", "再配置模式。", "最后验证输入。"],
        },
        "followUp": "请先回答第一道追问。",
        "uncertainties": [],
    }


class LearningTutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "question": "STM32 的 GPIO 输入模式应该怎样理解？",
            "profile": {"id": 7, "aiAnalysis": {"weaknesses": ["GPIO"]}},
            "knowledgeContext": [
                {"content": "GPIO 输入配置完成后，可从输入数据寄存器读取外部电平。"}
            ],
            "knowledgeSources": [
                {"id": "KB1", "title": "GPIO 课程讲义", "source": "gpio.txt", "section": 2}
            ],
        }

    def test_valid_llm_output_keeps_strict_guided_structure(self) -> None:
        with patch.object(learning_tutor, "call_llm_json", return_value=valid_tutor_raw()) as caller:
            result = learning_tutor.generate_learning_tutor(self.payload)
        self.assertEqual(caller.call_count, 1)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["schemaVersion"], "1.0")
        self.assertEqual(len(result["socraticQuestions"]), 3)
        self.assertEqual(len(result["hintLadder"]), 3)
        self.assertTrue(result["feynmanTask"]["prompt"])
        self.assertTrue(result["practiceTasks"][0]["acceptanceCriteria"])
        self.assertTrue(result["multimodal"]["mermaid"]["code"].startswith("flowchart"))
        self.assertEqual(result["references"][0]["id"], "KB1")
        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertEqual(learning_tutor.validate_tutor_output(result), [])

    def test_incomplete_first_output_requires_second_model_repair(self) -> None:
        with patch.object(
            learning_tutor,
            "call_llm_json",
            side_effect=[{"answer": "只给一个结论"}, valid_tutor_raw()],
        ) as caller:
            result = learning_tutor.generate_learning_tutor(self.payload)
        self.assertEqual(caller.call_count, 2)
        self.assertEqual(result["source"], "llm-repaired")
        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertFalse(result["generationWarnings"])

    def test_two_invalid_outputs_use_explicit_grounded_fallback(self) -> None:
        with patch.object(learning_tutor, "call_llm_json", side_effect=[{}, {}]) as caller:
            result = learning_tutor.generate_learning_tutor(self.payload)
        self.assertEqual(caller.call_count, 2)
        self.assertEqual(result["source"], "grounded-fallback")
        self.assertTrue(result["references"])
        self.assertTrue(result["uncertainties"])
        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertEqual(learning_tutor.validate_tutor_output(result), [])

    def test_unparseable_model_output_uses_explicit_grounded_fallback(self) -> None:
        with patch.object(
            learning_tutor,
            "call_llm_json",
            side_effect=ValueError("unterminated JSON"),
        ) as caller:
            result = learning_tutor.generate_learning_tutor(self.payload)
        self.assertEqual(caller.call_count, 1)
        self.assertEqual(result["source"], "grounded-fallback")
        self.assertIn("无法解析", "；".join(result["uncertainties"]))
        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertEqual(learning_tutor.validate_tutor_output(result), [])

    def test_unparseable_schema_repair_uses_explicit_grounded_fallback(self) -> None:
        with patch.object(
            learning_tutor,
            "call_llm_json",
            side_effect=[{"answer": "只有结论"}, ValueError("repair JSON truncated")],
        ) as caller:
            result = learning_tutor.generate_learning_tutor(self.payload)
        self.assertEqual(caller.call_count, 2)
        self.assertEqual(result["source"], "grounded-fallback")
        self.assertIn("修订结果仍无法解析", "；".join(result["uncertainties"]))
        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertEqual(learning_tutor.validate_tutor_output(result), [])

    def test_missing_knowledge_is_marked_uncertain(self) -> None:
        payload = {"question": "某芯片未提供手册时寄存器值是多少？"}
        with patch.object(learning_tutor, "call_llm_json", return_value=valid_tutor_raw()):
            result = learning_tutor.generate_learning_tutor(payload)
        self.assertFalse(result["references"])
        self.assertTrue(result["uncertainties"])
        self.assertTrue(result["qualityEvaluation"]["uncertaintyMarked"])

    def test_quality_reviewer_accepts_nested_harness_tutor_result(self) -> None:
        with patch.object(learning_tutor, "call_llm_json", return_value=valid_tutor_raw()):
            tutor = learning_tutor.generate_learning_tutor(self.payload)
        review = review_specialist_output(
            "smart_tutor",
            {"answer": tutor["answer"], "tutor": tutor},
            {"citations": tutor["references"]},
            75,
        )
        self.assertTrue(review["passed"])
        self.assertTrue(review["structuralOk"])
        self.assertFalse(review["retryRecommended"])

    def test_follow_up_prompt_keeps_exact_question_and_conversation_context(self) -> None:
        payload = {
            **self.payload,
            "question": "如果中断没有触发，我应该先检查哪三项？",
            "conversationContext": "上一轮主题：GPIO 中断\n我的回答或追问：如果中断没有触发，我应该先检查哪三项？",
            "previousTaskId": "xz_previous_tutor",
            "previousTurn": {
                "question": "GPIO 中断为什么没有触发？",
                "answer": "先确认中断配置链路。",
            },
        }
        prompts = []

        def capture_prompt(system: str, prompt: str, **kwargs) -> dict:
            prompts.append(prompt)
            return valid_tutor_raw()

        with patch.object(learning_tutor, "call_llm_json", side_effect=capture_prompt):
            result = learning_tutor.generate_learning_tutor(payload)

        self.assertEqual(result["question"], payload["question"])
        self.assertIn("当前用户问题（必须优先、精准回应）：如果中断没有触发，我应该先检查哪三项？", prompts[0])
        self.assertIn("我的回答或追问：如果中断没有触发，我应该先检查哪三项？", prompts[0])
        self.assertIn("先确认中断配置链路", prompts[0])


if __name__ == "__main__":
    unittest.main()
