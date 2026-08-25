from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import app as app_module
from backend import knowledge_growth
from backend.database_schema import init_auth_schema


DEMO_DIALOGUES = [
    {
        "topic": "STM32 与 FreeRTOS 学习目标",
        "user": "我想在八周内掌握 STM32 和 FreeRTOS，每天大约能学习一小时，希望最后能独立完成一个多任务环境监测项目。",
        "assistant": "已记录你的八周目标和每日一小时节奏。后续学习路径会先巩固 STM32 外设，再进入 FreeRTOS 任务调度、同步与综合项目。",
        "summary": "用户计划用八周、每天约一小时完成 STM32 到 FreeRTOS 的项目式学习，目标是独立实现多任务环境监测系统。",
    },
    {
        "topic": "DMA 环形缓冲区薄弱点",
        "user": "我总是弄不懂 DMA 环形缓冲区里写指针和读指针怎么更新，中断一多就容易把数据覆盖掉。",
        "assistant": "已将 DMA 指针更新和并发覆盖记录为薄弱点。下一轮会优先用时序图、剩余计数计算和可运行实验帮助你验证。",
        "summary": "用户在 DMA 环形缓冲区的读写指针、并发中断和数据覆盖处理上存在明确薄弱点。",
    },
    {
        "topic": "学习资源偏好",
        "user": "我更喜欢先看结构图和短视频，再到仿真实验里动手，不太喜欢一上来就读很长的文字资料。",
        "assistant": "已保存你的资源偏好。后续将优先推荐导图、短视频和仿真实验，并把长文档作为查阅材料。",
        "summary": "用户偏好结构图、短视频和仿真实验的学习顺序，长篇文字更适合作为补充查阅。",
    },
    {
        "topic": "Arduino 基础迁移到 RISC-V",
        "user": "我以前做过 Arduino 传感器项目，会用串口和 I2C，现在想从这些基础过渡到 RISC-V 单片机。",
        "assistant": "已识别你的 Arduino、串口和 I2C 基础。学习路径会复用已有外设经验，重点补充 RISC-V 架构、中断和工具链差异。",
        "summary": "用户已有 Arduino、串口和 I2C 项目经验，希望迁移到 RISC-V MCU 开发。",
    },
    {
        "topic": "LVGL 显示刷新调试",
        "user": "我的 LVGL 页面滑动时会卡顿，我希望用示波器和性能数据一步步排查，不想只看结论。",
        "assistant": "已记录 LVGL 卡顿问题和证据驱动的调试偏好。后续会围绕刷新区域、帧率、总线带宽和 DMA 配置组织排查任务。",
        "summary": "用户正在排查 LVGL 滑动卡顿，偏好通过示波器和性能数据逐步验证原因。",
    },
    {
        "topic": "TinyUSB 实验目标",
        "user": "我想做一个 TinyUSB HID 键盘实验，但不懂 USB 枚举过程，最好能边看状态变化边调试。",
        "assistant": "已将 USB 枚举列为本轮重点。后续会从描述符、控制传输和端点状态入手，并安排可观察状态变化的实验。",
        "summary": "用户希望完成 TinyUSB HID 键盘实验，当前薄弱点是 USB 枚举、描述符和控制传输过程。",
    },
]


def _timestamp(minutes_ago: int) -> str:
    return (datetime.now().astimezone() - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


def seed() -> dict[str, int | str]:
    with app_module.auth_db() as conn:
        init_auth_schema(conn)
        user = conn.execute("SELECT id FROM users WHERE username = 'admin123'").fetchone()
        if not user:
            raise RuntimeError("admin123 不存在，请先启动一次后端以初始化管理员账号。")
        user_id = int(user["id"])

        conn.execute(
            "DELETE FROM knowledge_growth_memories WHERE user_id = ? AND source_type = 'demo-conversation'",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM xiaozhi_messages WHERE user_id = ? AND intent_json LIKE '%knowledge-growth-demo%'",
            (user_id,),
        )

        old_collection = conn.execute(
            "SELECT id FROM private_knowledge_collections WHERE user_id = ? AND name = 'AI 知识库自生长演示库'",
            (user_id,),
        ).fetchone()
        if old_collection:
            collection_id = int(old_collection["id"])
            conn.execute("DELETE FROM knowledge_feedback_candidates WHERE user_id = ? AND collection_id = ?", (user_id, collection_id))
            conn.execute("DELETE FROM private_knowledge_chunks WHERE user_id = ? AND collection_id = ?", (user_id, collection_id))
            conn.execute("DELETE FROM private_knowledge_documents WHERE user_id = ? AND collection_id = ?", (user_id, collection_id))
            conn.execute("DELETE FROM private_knowledge_collections WHERE user_id = ? AND id = ?", (user_id, collection_id))
        legacy_title_prefix = "\u7b54\u8fa9\u6f14\u793a"
        conn.execute(
            "DELETE FROM knowledge_feedback_candidates WHERE user_id = ? AND title LIKE ?",
            (user_id, f"{legacy_title_prefix} · %"),
        )
        conn.execute("DELETE FROM agent_orchestration_runs WHERE user_id = ? AND run_id LIKE 'demo-knowledge-growth-%'", (user_id,))

        for index, dialogue in enumerate(DEMO_DIALOGUES, start=1):
            created_at = _timestamp(42 - index * 5)
            intent = json.dumps({"demo": "knowledge-growth-demo", "topic": dialogue["topic"]}, ensure_ascii=False)
            user_cursor = conn.execute(
                """
                INSERT INTO xiaozhi_messages (user_id, role, content, intent_json, cards_json, created_at)
                VALUES (?, 'user', ?, ?, '[]', ?)
                """,
                (user_id, dialogue["user"], intent, created_at),
            )
            assistant_cursor = conn.execute(
                """
                INSERT INTO xiaozhi_messages (user_id, role, content, intent_json, cards_json, created_at)
                VALUES (?, 'assistant', ?, ?, '[]', ?)
                """,
                (user_id, dialogue["assistant"], intent, created_at),
            )
            knowledge_growth.record_conversation_memory(
                conn,
                user_id,
                source_type="demo-conversation",
                source_key=f"demo-{index:02d}",
                session_id="示例对话",
                route="/knowledge-network",
                user_message=dialogue["user"],
                assistant_message=dialogue["assistant"],
                metadata={
                    "demo": True,
                    "topic": dialogue["topic"],
                    "summary": dialogue["summary"],
                    "userMessageId": int(user_cursor.lastrowid),
                    "assistantMessageId": int(assistant_cursor.lastrowid),
                },
                timestamp=created_at,
            )

        overview = knowledge_growth.conversation_growth_overview(conn, user_id, limit=100)
        return {"username": "admin123", **overview["stats"]}


if __name__ == "__main__":
    print(json.dumps(seed(), ensure_ascii=False, indent=2))
