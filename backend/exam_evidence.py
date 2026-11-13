"""Answer evidence must distinguish unanswered, ungraded, correct and incorrect."""
import json


def has_answer(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(has_answer(x) for x in value)
    if isinstance(value, dict):
        return any(has_answer(x) for x in value.values())
    return True


QUESTION_RESOURCE_TYPES = {"quiz", "question-bank", "question_bank", "question-generator", "exam", "exercise", "questions"}


def learning_resource_completed(resource_type, payload):
    if str(resource_type or payload.get("resourceType") or "").lower() in QUESTION_RESOURCE_TYPES:
        return bool(payload.get("completionSource") == "exam-submission" and payload.get("examResultId") and payload.get("submittedAt"))
    feedback = payload.get("learningFeedback") or {}
    return bool((payload.get("viewedAt") and payload.get("viewSource") == "learning-path-task-open") or (payload.get("completionSource") == "learning-feedback" and feedback.get("outcome") == "completed"))


def resource_sheet_ids(value, depth=0):
    if depth > 8:
        return set()
    ids = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"sheet_id", "sheetId", "questionSheetId"} and item is not None:
                ids.add(str(item))
            if key in {"sheet", "question_sheet", "questionSheet"} and isinstance(item, dict) and item.get("id") is not None:
                ids.add(str(item["id"]))
            if isinstance(item, (dict, list)):
                ids.update(resource_sheet_ids(item, depth + 1))
    elif isinstance(value, list):
        for item in value:
            ids.update(resource_sheet_ids(item, depth + 1))
    return ids


def answer_state(item):
    if not has_answer(item.get("user_answer", item.get("userAnswer"))):
        return "unanswered"
    if item.get("grading_status") in {"pending", "ungraded"}:
        return "ungraded"
    flag = item.get("correct", item.get("isCorrect"))
    if flag is True or flag == 1 or flag == "true":
        return "correct"
    if flag is False or flag == 0 or flag == "false":
        return "incorrect"
    return "ungraded"


def normalize_exam(payload):
    result = dict(payload)
    details = payload.get("detail") or []
    if isinstance(details, dict):
        details = details.get("items") or details.get("details") or []
    items, counts = [], {key: 0 for key in ("correct", "incorrect", "unanswered", "ungraded")}
    for raw in details:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        state = answer_state(item)
        counts[state] += 1
        item.update(answer_status=state, answered=state != "unanswered", correct=True if state == "correct" else False if state == "incorrect" else None)
        items.append(item)
    result.update(detail=items, correct_count=counts["correct"], incorrect_count=counts["incorrect"], unanswered_count=counts["unanswered"], ungraded_count=counts["ungraded"], answered_count=len(items)-counts["unanswered"], graded_count=counts["correct"]+counts["incorrect"])
    return result


def ensure_exam_columns(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(exam_results)")}
    for name in ("profile_report_id", "answered_count", "incorrect_count", "unanswered_count", "ungraded_count"):
        if name not in columns:
            connection.execute(f"ALTER TABLE exam_results ADD COLUMN {name} INTEGER")


def migrate_exam_evidence(connection):
    ensure_exam_columns(connection)
    connection.execute("CREATE TABLE IF NOT EXISTS exam_evidence_migration_audit (exam_id INTEGER PRIMARY KEY, original_detail_json TEXT NOT NULL, migrated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    columns = [x[1] for x in connection.execute("PRAGMA table_info(exam_results)")]
    updated = 0
    for raw in connection.execute("SELECT * FROM exam_results").fetchall():
        row = dict(zip(columns, raw))
        normalized = normalize_exam({"detail": json.loads(row["detail_json"])})
        text = json.dumps(normalized["detail"], ensure_ascii=False)
        names = ("answered_count", "incorrect_count", "unanswered_count", "ungraded_count")
        values = [normalized[k] for k in names]
        if row["detail_json"] == text and all(row[k] == v for k, v in zip(names, values)):
            continue
        connection.execute("INSERT OR IGNORE INTO exam_evidence_migration_audit(exam_id, original_detail_json) VALUES (?, ?)", (row["id"], row["detail_json"]))
        connection.execute("UPDATE exam_results SET detail_json=?, answered_count=?, incorrect_count=?, unanswered_count=?, ungraded_count=? WHERE id=?", [text, *values, row["id"]])
        updated += 1
    return updated
