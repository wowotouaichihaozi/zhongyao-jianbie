from copy import deepcopy

from backend.mcu_catalog import (
    MCU_BOARDS,
    MCU_COMPONENTS,
    MCU_EXPERIMENTS,
    mcu_catalog_payload,
    normalize_mcu_resource_params,
    normalize_mcu_route,
    recommend_mcu_experiments,
    validate_mcu_flash,
)


def _error_codes(result):
    return {item["code"] for item in result["diagnostics"]["errors"]}


def _warning_codes(result):
    return {item["code"] for item in result["diagnostics"]["warnings"]}


def test_catalog_contains_complete_boards_components_presets_and_sources():
    catalog = mcu_catalog_payload()

    assert catalog["counts"] == {"boards": 2, "components": 17, "experiments": 21}
    assert len(MCU_COMPONENTS) == 17
    assert len(MCU_EXPERIMENTS) == 21
    assert all(len(experiment["steps"]) == 5 for experiment in catalog["experiments"])
    arduino = next(board for board in MCU_BOARDS if board["id"] == "arduino")
    mcs51 = next(board for board in MCU_BOARDS if board["id"] == "8051")
    assert {pin["id"] for pin in arduino["pins"]} >= {"D0", "D13", "A0", "A5", "5V", "GND1"}
    assert len(mcs51["pins"]) == 40
    assert {pin["physicalPin"] for pin in mcs51["pins"]} == {str(number) for number in range(1, 41)}
    assert {source["license"] for source in catalog["sources"]} == {"MIT", "CC0-1.0"}


def test_every_preset_passes_source_and_wiring_validation():
    failures = {}
    for experiment in MCU_EXPERIMENTS:
        result = validate_mcu_flash({"projectId": experiment["id"]})
        if not result["valid"]:
            failures[experiment["id"]] = result["diagnostics"]["errors"]

    assert failures == {}


def test_arduino_source_rejects_pwm_on_non_pwm_pin():
    result = validate_mcu_flash(
        {
            "board": "arduino",
            "code": "void setup() { pinMode(2, OUTPUT); }\nvoid loop() { analogWrite(2, 128); }",
            "parts": [],
        }
    )

    assert result["valid"] is False
    assert "SOURCE_PIN_CAPABILITY_MISMATCH" in _error_codes(result)


def test_arduino_source_rejects_unsupported_block_control_flow():
    result = validate_mcu_flash(
        {
            "board": "arduino",
            "code": "void setup() {}\nvoid loop() { for (int i = 0; i < 3; i++) { digitalWrite(13, HIGH); } }",
            "parts": [],
        }
    )

    assert result["valid"] is False
    assert "UNSUPPORTED_ARDUINO_CALL" in _error_codes(result)


def test_i2c_terminal_rejects_regular_analog_pin():
    experiment = next(item for item in MCU_EXPERIMENTS if item["id"] == "uno-i2c-oled")
    parts = deepcopy(experiment["parts"])
    oled = next(part for part in parts if part["componentId"] == "oled-i2c")
    oled["connections"]["SDA"] = "A0"

    result = validate_mcu_flash(
        {"board": "arduino", "projectId": experiment["id"], "code": experiment["code"], "parts": parts}
    )

    assert result["valid"] is False
    assert "PIN_CAPABILITY_MISMATCH" in _error_codes(result)


def test_required_component_terminal_must_be_connected():
    result = validate_mcu_flash(
        {
            "board": "arduino",
            "code": "void setup() { pinMode(13, OUTPUT); }\nvoid loop() { digitalWrite(13, HIGH); }",
            "parts": [
                {
                    "id": "led",
                    "componentId": "led-module",
                    "label": "LED",
                    "connections": {"A": "D13"},
                }
            ],
        }
    )

    assert result["valid"] is False
    assert "TERMINAL_UNCONNECTED" in _error_codes(result)


def test_8051_p0_output_warns_about_external_pullup():
    result = validate_mcu_flash(
        {
            "board": "8051",
            "code": "ORG 0000H\nCLR P0.0\nSJMP $\nEND",
            "parts": [
                {
                    "id": "led",
                    "componentId": "led-module",
                    "label": "P0 LED",
                    "connections": {"A": "P0.0", "K": "GND"},
                }
            ],
        }
    )

    assert result["valid"] is True
    assert "P0_PULLUP_REQUIRED" in _warning_codes(result)


def test_profile_context_changes_recommendation_order():
    recommendations = recommend_mcu_experiments(
        profile_context={"weakPoints": ["PWM 占空比与呼吸灯控制薄弱"]},
        limit=4,
    )

    assert recommendations[0]["id"] == "uno-pwm-fade"
    assert "PWM" in recommendations[0]["recommendation"]["reason"]


def test_recommendation_honors_requested_board_as_a_hard_constraint():
    recommendations = recommend_mcu_experiments(
        {"board": "8051", "topic": "PWM 占空比"},
        profile_context={"weakPoints": ["PWM 占空比"]},
        limit=6,
    )

    assert recommendations
    assert all(item["board"] == "8051" for item in recommendations)


def test_auto_recommendation_can_exclude_completed_experiments():
    recommendations = recommend_mcu_experiments(
        {"board": "arduino", "topic": "PWM 呼吸灯", "excludeCompleted": True},
        profile_context={"weakPoints": ["PWM 占空比"]},
        history=[{"experiment_id": "uno-pwm-fade", "passed": True}],
        limit=4,
    )

    assert recommendations
    assert all(item["id"] != "uno-pwm-fade" for item in recommendations)


def test_oled_recommendation_does_not_match_plain_led_by_substring():
    recommendations = recommend_mcu_experiments(
        profile_context={"weakPoints": ["I2C OLED 总线与地址配置"]},
        limit=3,
    )

    assert recommendations[0]["id"] == "uno-i2c-oled"
    plain_led = next(item for item in recommendations if item["id"] == "uno-led-ready")
    assert "覆盖 LED" not in plain_led["recommendation"]["reason"]


def test_virtual_firmware_identifier_is_stable_for_same_inputs():
    payload = {"projectId": "uno-led-ready"}

    first = validate_mcu_flash(deepcopy(payload))
    second = validate_mcu_flash(deepcopy(payload))

    assert first["firmware"]["id"] == second["firmware"]["id"]
    assert first["firmware"]["engine"] == "teaching-simulator"


def test_normalize_mcu_route_preserves_task_query_and_uses_supported_project():
    params = {
        "board": "STM32F103C8T6",
        "projectId": "gpio-led-button-demo",
        "topic": "STM32 GPIO 按键输入",
    }

    normalized = normalize_mcu_resource_params(params)
    route = normalize_mcu_route(
        "/personalized-resources/mcu-simulator/STM32F103C8T6/gpio-led-button-demo?source=learning-path&xzTask=xz_123",
        params,
    )

    assert normalized["board"] == "arduino"
    assert normalized["projectId"] == "uno-button-ready"
    assert route == "/personalized-resources/mcu-simulator/arduino/uno-button-ready?source=learning-path&xzTask=xz_123"


def test_normalize_mcu_params_keeps_supported_8051_ram_project():
    normalized = normalize_mcu_resource_params(
        {
            "board": "8051",
            "projectId": "8051-ram-ready",
            "topic": "RAM 寻址实验",
        }
    )

    assert normalized["board"] == "8051"
    assert normalized["projectId"] == "8051-ram-ready"
    assert "simulatorAdaptation" not in normalized
