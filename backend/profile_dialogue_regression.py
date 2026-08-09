from __future__ import annotations

import json
import sys
import time

from learning_profile_workflow_agent import (
    clear_persisted_profile_dialogue,
    is_filled,
    run_learning_profile_workflow,
)


OPENING = (
    "\u4f60\u597d\uff0c\u6211\u662f\u4f60\u7684\u6570\u5b57\u4eba AI "
    "\u8bb2\u5e08\uff0c\u4f1a\u966a\u4f60\u68b3\u7406\u5d4c\u5165\u5f0f"
    "\u5b66\u4e60\u753b\u50cf\u3002\u4f60\u73b0\u5728\u4e3b\u8981\u5728"
    "\u5b66\u5d4c\u5165\u5f0f\u7684\u54ea\u4e00\u90e8\u5206\uff0c\u6bd4"
    "\u5982 STM32\u3001\u5355\u7247\u673a\u3001Linux \u9a71\u52a8\u8fd8"
    "\u662f\u5f00\u53d1\u677f\u9879\u76ee\uff1f"
)


SCENARIOS = [
    {
        "name": "embedded_profile_core_path",
        "inputs": [
            "STM32",
            "\u53c2\u52a0\u667a\u80fd\u8f66\u7ade\u8d5b",
            "GPIO",
            "20\u5c0f\u65f6",
            "\u786c\u4ef6\u63a5\u7ebf",
            "\u5148\u770b\u539f\u7406\u56fe\u89e3\uff0c\u8ddf\u7740\u6848\u4f8b\u4e00\u6b65\u6b65\u505a",
            "\u89c6\u9891\u8bb2\u89e3\u548c\u4ee3\u7801\u4f8b\u7a0b",
            "\u5faa\u5e8f\u6e10\u8fdb",
        ],
        "required_dimensions": [
            "\u4e13\u4e1a/\u8bfe\u7a0b\u80cc\u666f",
            "\u5b66\u4e60\u76ee\u6807",
            "\u5f53\u524d\u77e5\u8bc6\u57fa\u7840",
            "\u5b66\u4e60\u8fdb\u5ea6",
            "\u8584\u5f31\u77e5\u8bc6\u70b9",
            "\u6613\u9519\u70b9\u7c7b\u578b",
            "\u5b66\u4e60\u98ce\u683c/\u8ba4\u77e5\u504f\u597d",
            "\u8d44\u6e90\u5f62\u5f0f\u504f\u597d",
            "\u53ef\u6295\u5165\u65f6\u95f4",
            "\u96be\u5ea6\u63a5\u53d7\u7a0b\u5ea6",
        ],
    }
]


def compact_profile(profile: dict) -> dict:
    return {k: v for k, v in profile.items() if k != "\u8865\u5145\u4fe1\u606f"}


def run_scenario(scenario: dict) -> bool:
    user_id = f"regression-{scenario['name']}-{int(time.time())}"
    clear_persisted_profile_dialogue(user_id)
    messages = [{"role": "assistant", "content": OPENING}]
    previous_reply = OPENING
    result = {}

    print(f"\n=== {scenario['name']} ===")
    for index, user_text in enumerate(scenario["inputs"], 1):
        messages.append({"role": "user", "content": user_text})
        started = time.time()
        result = run_learning_profile_workflow(messages, user_id=user_id, verbose=False)
        elapsed = time.time() - started
        reply = (result.get("reply") or "").strip()
        profile = compact_profile(result.get("studentProfile") or {})
        missing = result.get("missingProfileDimensions") or []
        next_dimension = result.get("nextDimension") or ""
        evidence = result.get("workflow", {}).get("candidateEvidence") or []

        print(f"\nturn={index} user={user_text} elapsed={elapsed:.2f}s")
        print(f"reply={reply}")
        print(f"next={next_dimension} missing={missing}")
        print(f"evidence={json.dumps(evidence, ensure_ascii=False)[:900]}")

        if not reply:
            print("FAIL: empty reply")
            return False
        if reply == previous_reply:
            print("FAIL: exact repeated reply")
            return False
        if next_dimension and is_filled(profile.get(next_dimension)):
            print("FAIL: next dimension is already filled")
            return False

        messages.append({"role": "assistant", "content": reply})
        previous_reply = reply

    profile = compact_profile(result.get("studentProfile") or {})
    missing_required = [
        dimension
        for dimension in scenario["required_dimensions"]
        if not is_filled(profile.get(dimension))
    ]
    print("\nfinal_profile=" + json.dumps(profile, ensure_ascii=False, indent=2))
    if missing_required:
        print("FAIL: missing required dimensions " + json.dumps(missing_required, ensure_ascii=False))
        return False
    print("PASS")
    return True


def main() -> int:
    ok = True
    for scenario in SCENARIOS:
        ok = run_scenario(scenario) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
