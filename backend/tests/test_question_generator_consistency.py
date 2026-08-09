from backend.question_generator_runtime import normalize_question_bank_technical_consistency
from backend.resource_workflow import evaluate_question_bank_resource


def test_stm32f1_api_conflicts_are_corrected_before_persistence():
    bank = {
        "title": "STM32F103 GPIO 题库",
        "questions": [
            {
                "id": "Q1",
                "type": "单选题",
                "stem": "STM32F103 的 EXTI 映射缺少哪一步？",
                "options": [
                    "A. 调用 SYSCFG_EXTILineConfig()",
                    "B. 设置 GPIO_InitStruct.GPIO_PuPd 为 GPIO_PUPD_PULLUP",
                ],
                "answer": "A",
                "analysis": "STM32F103 需要调用 SYSCFG_EXTILineConfig() 完成映射。",
            }
        ],
    }

    corrections = normalize_question_bank_technical_consistency(
        bank,
        {
            "course_name": "STM32F103",
            "target_topic": "GPIO 与 EXTI",
            "resource_plan_result": "GPIO_EXTILineConfig GPIO_InitStruct.GPIO_Mode GPIO_Mode_IPU",
        },
    )

    rendered = " ".join(
        [
            bank["questions"][0]["stem"],
            *bank["questions"][0]["options"],
            bank["questions"][0]["analysis"],
        ]
    )
    assert "SYSCFG_EXTILineConfig" not in rendered
    assert "GPIO_EXTILineConfig" in rendered
    assert "GPIO_Mode_IPU" in rendered
    assert len(corrections) == 3


def test_unsupported_register_claim_is_replaced_by_grounded_question():
    bank = {
        "title": "GPIO 题库",
        "questions": [
            {
                "id": "Q1",
                "type": "单选题",
                "stem": "写入 GPIOA->CRL 后为什么会触发总线错误？",
                "options": ["A. RCC_APB2ENR 未清零", "B. 其他"],
                "answer": "A",
                "analysis": "GPIOA->CRL 与 RCC_APB2ENR 会发生总线仲裁冲突。",
            }
        ],
    }

    corrections = normalize_question_bank_technical_consistency(
        bank,
        {
            "course_name": "STM32",
            "target_topic": "GPIO",
            "resource_plan_result": "课程资料仅说明 GPIO、调试工具和 STM32F103 基础架构。",
        },
    )

    question = bank["questions"][0]
    rendered = " ".join([question["stem"], *question["options"], question["analysis"]])
    assert "GPIOA->CRL" not in rendered
    assert "RCC_APB2ENR" not in rendered
    assert "[KB1]" in question["analysis"]
    assert corrections[-1]["to"] == "knowledge-grounded-safe-question"


def test_question_quality_exposes_technical_consistency_penalty():
    bank = {
        "questions": [
            {
                "id": "Q1",
                "type": "单选题",
                "stem": "GPIO 时钟如何使能？",
                "answer": "A",
                "analysis": "通过 RCC 使能。",
            }
        ],
        "technical_corrections": [
            {
                "questionId": "Q1",
                "from": "SYSCFG_EXTILineConfig",
                "to": "GPIO_EXTILineConfig",
            }
        ],
    }

    quality = evaluate_question_bank_resource(bank, expected_count=1, citations=[{"id": "KB1"}])

    assert quality["technicalCorrectionCount"] == 1
    assert quality["technicalConsistencyPenalty"] == 4
    assert quality["score"] < 100
    assert quality["passed"] is True
