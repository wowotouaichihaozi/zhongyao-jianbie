from __future__ import annotations

import unittest
from unittest.mock import patch

from learning_animation import evaluate_learning_animation, generate_learning_animation


def valid_storyboard() -> dict:
    return {
        "title": "STM32 外部中断响应动画",
        "subtitle": "从边沿到中断服务",
        "audience": "STM32 初学者",
        "learningObjectives": ["解释触发流程", "完成按键中断验证"],
        "scenes": [
            {
                "title": "输入边沿",
                "durationSeconds": 12,
                "narration": "按键产生输入边沿，EXTI 线路检测状态变化。[KB1]",
                "visualType": "signal",
                "headline": "边沿检测",
                "primaryLabel": "按键输入",
                "secondaryLabel": "EXTI",
                "steps": ["输入变化", "边沿检测"],
                "keyPoints": ["上升沿", "下降沿"],
                "codeSnippet": "",
                "signal": {"input": "GPIO", "process": "EXTI", "output": "Pending"},
            },
            {
                "title": "挂起与请求",
                "durationSeconds": 14,
                "narration": "挂起位置位后向 NVIC 发出中断请求。[KB1]",
                "visualType": "register",
                "headline": "挂起标志",
                "primaryLabel": "EXTI_PR",
                "secondaryLabel": "NVIC",
                "steps": ["置位", "判优"],
                "keyPoints": ["挂起状态", "优先级"],
                "codeSnippet": "",
                "signal": {"input": "Pending", "process": "NVIC", "output": "IRQ"},
            },
            {
                "title": "服务函数",
                "durationSeconds": 16,
                "narration": "处理器进入服务函数并执行最小业务逻辑。[KB1]",
                "visualType": "code",
                "headline": "IRQ Handler",
                "primaryLabel": "ISR",
                "secondaryLabel": "业务处理",
                "steps": ["保存现场", "执行 ISR"],
                "keyPoints": ["服务函数保持简短"],
                "codeSnippet": "void EXTI0_IRQHandler(void) {\n  __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_0);\n}",
                "signal": {"input": "IRQ", "process": "ISR", "output": "处理结果"},
            },
            {
                "title": "清除与验证",
                "durationSeconds": 18,
                "narration": "清除挂起标志并再次触发，验证系统可以持续响应。[KB1]",
                "visualType": "experiment",
                "headline": "闭环验证",
                "primaryLabel": "开发板",
                "secondaryLabel": "LED 翻转",
                "steps": ["清除标志", "再次按键", "观察 LED"],
                "keyPoints": ["保留运行证据"],
                "codeSnippet": "",
                "signal": {"input": "按键", "process": "ISR", "output": "LED"},
            },
        ],
        "recap": ["边沿检测", "中断请求", "服务处理", "清除验证"],
        "knowledgeChecks": [
            {"question": "为什么要清除挂起标志？", "answer": "避免中断持续挂起。", "explanation": "形成可重复响应闭环。"}
        ],
        "references": [{"id": "KB1"}],
        "uncertainties": [],
    }


class LearningAnimationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "topic": "STM32 外部中断响应",
            "requirements": "用信号流和代码解释",
            "profile": {
                "id": 42,
                "chatStudentProfile": {"学习目标": ["完成按键中断实验"], "资源偏好": "动画和实验"},
                "aiAnalysis": {"learningStyle": "视觉化", "weaknesses": ["挂起标志"]},
            },
            "knowledgeSources": [
                {"citationId": "KB1", "title": "中断系统原理", "source": "22_中断系统原理.txt", "section": 2}
            ],
            "knowledgeContext": [
                {"citationId": "KB1", "title": "中断系统原理", "excerpt": "中断请求经 NVIC 判优后进入服务函数。"}
            ],
        }

    def test_generates_grounded_animation_with_quality_evaluation(self) -> None:
        with patch("learning_animation.call_llm_json", return_value=valid_storyboard()):
            result = generate_learning_animation(self.payload)

        animation = result["animation"]
        self.assertEqual(len(animation["scenes"]), 4)
        self.assertEqual(animation["profile"]["profileReportId"], 42)
        self.assertEqual(animation["references"][0]["id"], "KB1")
        self.assertGreaterEqual(len({item["visualType"] for item in animation["scenes"]}), 3)
        self.assertTrue(result["qualityEvaluation"]["passed"])

    def test_repairs_storyboard_with_too_few_scenes(self) -> None:
        invalid = {**valid_storyboard(), "scenes": valid_storyboard()["scenes"][:2]}
        with patch("learning_animation.call_llm_json", side_effect=[invalid, valid_storyboard()]) as model:
            result = generate_learning_animation(self.payload)

        self.assertEqual(model.call_count, 2)
        self.assertEqual(result["source"], "llm-schema-repaired")
        self.assertTrue(result["qualityEvaluation"]["passed"])

    def test_normalizes_structured_scene_steps_and_key_points(self) -> None:
        storyboard = valid_storyboard()
        storyboard["scenes"][0]["steps"] = [
            {"title": "中断触发条件", "content": "外设信号向 CPU 发出中断请求"},
            {"label": "优先级判断", "description": "NVIC 选择当前最高优先级请求"},
        ]
        storyboard["scenes"][0]["keyPoints"] = [
            {"name": "边沿选择", "text": "根据输入信号选择上升沿或下降沿"}
        ]

        with patch("learning_animation.call_llm_json", return_value=storyboard):
            result = generate_learning_animation(self.payload)

        scene = result["animation"]["scenes"][0]
        self.assertEqual(scene["steps"][0], "中断触发条件：外设信号向 CPU 发出中断请求")
        self.assertEqual(scene["steps"][1], "优先级判断：NVIC 选择当前最高优先级请求")
        self.assertEqual(scene["keyPoints"][0], "边沿选择：根据输入信号选择上升沿或下降沿")
        self.assertFalse(any("{" in item or "}" in item for item in scene["steps"] + scene["keyPoints"]))

    def test_model_failure_returns_playable_grounded_fallback(self) -> None:
        with patch("learning_animation.call_llm_json", side_effect=RuntimeError("model timeout")):
            result = generate_learning_animation(self.payload)

        self.assertEqual(result["source"], "knowledge-template-fallback")
        self.assertEqual(len(result["animation"]["scenes"]), 4)
        self.assertTrue(result["qualityEvaluation"]["passed"])

    def test_quality_rejects_sensitive_content(self) -> None:
        animation = valid_storyboard()
        animation["scenes"][0]["narration"] = "api_key=1234567890abcdefghijklmnop"
        quality = evaluate_learning_animation(animation, self.payload["profile"])
        self.assertFalse(quality["passed"])
        self.assertIn("检测到疑似敏感凭据", quality["issues"])


if __name__ == "__main__":
    unittest.main()
