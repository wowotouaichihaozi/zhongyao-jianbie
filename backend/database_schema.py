import json
import re
import sqlite3
from pathlib import Path


AUTH_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'enabled',
    avatar_url TEXT NOT NULL DEFAULT '/userlogo.png',
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER NOT NULL DEFAULT 0,
    ip TEXT,
    user_agent TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mcu_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    experiment_id TEXT NOT NULL,
    experiment_name TEXT NOT NULL DEFAULT '',
    passed INTEGER NOT NULL DEFAULT 0,
    weak_points TEXT NOT NULL DEFAULT '[]',
    run_data TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_profile_questionnaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    section_statuses TEXT NOT NULL DEFAULT '{}',
    questionnaire_data TEXT NOT NULL DEFAULT '{}',
    missing_message TEXT NOT NULL DEFAULT '暂时缺失该部分的数据',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_profile_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    report_json TEXT NOT NULL,
    profile_name TEXT NOT NULL DEFAULT '学习画像',
    version INTEGER NOT NULL DEFAULT 1,
    parent_report_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(parent_report_id) REFERENCES learning_profile_reports(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS learning_profile_portraits (
    report_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    image_blob BLOB,
    mime_type TEXT NOT NULL DEFAULT 'image/png',
    source TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'ready',
    error TEXT NOT NULL DEFAULT '',
    generation_token TEXT NOT NULL DEFAULT '',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(report_id) REFERENCES learning_profile_reports(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_learning_profile_state (
    user_id INTEGER PRIMARY KEY,
    active_report_id INTEGER,
    generation INTEGER NOT NULL DEFAULT 0,
    reset_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(active_report_id) REFERENCES learning_profile_reports(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS learning_profile_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '新学习画像',
    status TEXT NOT NULL DEFAULT 'collecting',
    dimensions_json TEXT NOT NULL DEFAULT '{}',
    report_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(report_id) REFERENCES learning_profile_reports(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS learning_profile_session_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES learning_profile_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS system_schema_migrations (
    migration_key TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS xiaozhi_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    route TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_activity_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    route TEXT NOT NULL DEFAULT '',
    route_name TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    active_seconds INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    ended_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, session_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER,
    task_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    resource_type TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    route TEXT NOT NULL DEFAULT '',
    cache_key TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL DEFAULT 'completed',
    difficulty TEXT NOT NULL DEFAULT 'appropriate',
    helpful INTEGER,
    rating INTEGER,
    note TEXT NOT NULL DEFAULT '',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(profile_report_id) REFERENCES learning_profile_reports(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS xiaozhi_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    intent_json TEXT NOT NULL DEFAULT '{}',
    cards_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS multimodal_inputs (
    input_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    context_type TEXT NOT NULL DEFAULT 'chat',
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    media_kind TEXT NOT NULL DEFAULT 'file',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    extracted_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS xiaozhi_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    route TEXT NOT NULL DEFAULT '',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generated_video_covers (
    task_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER NOT NULL DEFAULT 0,
    image_blob BLOB,
    mime_type TEXT NOT NULL DEFAULT 'image/jpeg',
    model TEXT NOT NULL DEFAULT 'z-image-turbo',
    prompt TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES xiaozhi_tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_orchestration_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    task_id TEXT NOT NULL DEFAULT '',
    user_id INTEGER NOT NULL,
    root_agent TEXT NOT NULL DEFAULT 'xiaozhi-companion-agent',
    task_type TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'running',
    architecture TEXT NOT NULL DEFAULT 'supervisor-shared-blackboard',
    harness_name TEXT NOT NULL DEFAULT '',
    harness_version TEXT NOT NULL DEFAULT '',
    skill_id TEXT NOT NULL DEFAULT '',
    mcp_server TEXT NOT NULL DEFAULT '',
    mcp_tool TEXT NOT NULL DEFAULT '',
    policy_json TEXT NOT NULL DEFAULT '{}',
    profile_report_id INTEGER NOT NULL DEFAULT 0,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    review_json TEXT NOT NULL DEFAULT '{}',
    feedback_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_orchestration_handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    artifact_type TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES agent_orchestration_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_orchestration_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    progress INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES agent_orchestration_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_agent_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER NOT NULL,
    supervisor_agent TEXT NOT NULL DEFAULT 'xiaozhi-companion-agent',
    summary_text TEXT NOT NULL DEFAULT '',
    summary_version INTEGER NOT NULL DEFAULT 0,
    compacted_through_sequence INTEGER NOT NULL DEFAULT 0,
    message_count INTEGER NOT NULL DEFAULT 0,
    estimated_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, profile_report_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(profile_report_id) REFERENCES learning_profile_reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    dedupe_key TEXT NOT NULL,
    run_id TEXT NOT NULL DEFAULT '',
    task_id TEXT NOT NULL DEFAULT '',
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL DEFAULT '',
    message_type TEXT NOT NULL DEFAULT 'status',
    status TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    resource_refs_json TEXT NOT NULL DEFAULT '[]',
    estimated_tokens INTEGER NOT NULL DEFAULT 0,
    compacted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(conversation_id, sequence),
    UNIQUE(conversation_id, dedupe_key),
    FOREIGN KEY(conversation_id) REFERENCES profile_agent_conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_agent_context_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    source_message_count INTEGER NOT NULL DEFAULT 0,
    source_estimated_tokens INTEGER NOT NULL DEFAULT 0,
    through_sequence INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(conversation_id, version),
    FOREIGN KEY(conversation_id) REFERENCES profile_agent_conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_graph_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    concept_key TEXT NOT NULL,
    label TEXT NOT NULL,
    domain TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'derived',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, concept_key),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_key TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    run_id TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(user_id, source_type, source_key, target_type, target_key, relation, run_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_feedback_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    collection_id INTEGER NOT NULL,
    run_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    review_note TEXT NOT NULL DEFAULT '',
    reviewed_by INTEGER,
    reviewed_at TEXT NOT NULL DEFAULT '',
    approved_document_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(collection_id) REFERENCES private_knowledge_collections(id) ON DELETE CASCADE,
    FOREIGN KEY(reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY(approved_document_id) REFERENCES private_knowledge_documents(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS knowledge_growth_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_key TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    route TEXT NOT NULL DEFAULT '',
    user_message TEXT NOT NULL,
    assistant_message TEXT NOT NULL DEFAULT '',
    core_summary TEXT NOT NULL DEFAULT '',
    topics_json TEXT NOT NULL DEFAULT '[]',
    signals_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'captured',
    extractor TEXT NOT NULL DEFAULT 'structured-dialogue-memory-v1',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, source_type, source_key),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_agent_runtime_settings (
    user_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0,
    protocol TEXT NOT NULL DEFAULT 'openai',
    base_url TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT 'astron-code-latest',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_path_configs (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_learning_path_configs (
    user_id INTEGER PRIMARY KEY,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_path_profile_configs (
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id, profile_report_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(profile_report_id) REFERENCES learning_profile_reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_path_node_caches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    cache_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    resource_type TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    route TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, cache_key),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generated_learning_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER,
    task_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    document_json TEXT NOT NULL DEFAULT '{}',
    quality_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(profile_report_id) REFERENCES learning_profile_reports(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS learning_effect_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_report_id INTEGER NOT NULL,
    run_id TEXT NOT NULL DEFAULT '',
    assessment_json TEXT NOT NULL DEFAULT '{}',
    path_adjustment_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'evaluated',
    created_at TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(profile_report_id) REFERENCES learning_profile_reports(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS private_knowledge_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, name),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_private_knowledge_state (
    user_id INTEGER PRIMARY KEY,
    active_collection_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(active_collection_id) REFERENCES private_knowledge_collections(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS private_knowledge_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    collection_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    byte_size INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready',
    error TEXT NOT NULL DEFAULT '',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    content_blob BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, collection_id, sha256),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(collection_id) REFERENCES private_knowledge_collections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS private_knowledge_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    collection_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    page INTEGER,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(document_id, chunk_index),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(collection_id) REFERENCES private_knowledge_collections(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES private_knowledge_documents(id) ON DELETE CASCADE
);
"""


AUTH_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_mcu_experiments_user_id ON mcu_experiments(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_profile_questionnaires_user_id ON learning_profile_questionnaires(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_profile_reports_user_id ON learning_profile_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_profile_reports_parent_id ON learning_profile_reports(parent_report_id);
CREATE INDEX IF NOT EXISTS idx_learning_profile_reports_user_version ON learning_profile_reports(user_id, version);
CREATE INDEX IF NOT EXISTS idx_learning_profile_portraits_user_id ON learning_profile_portraits(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_profile_portraits_status ON learning_profile_portraits(status);
CREATE INDEX IF NOT EXISTS idx_user_learning_profile_state_active ON user_learning_profile_state(active_report_id);
CREATE INDEX IF NOT EXISTS idx_learning_profile_sessions_user_updated ON learning_profile_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_profile_session_messages_session_id ON learning_profile_session_messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_xiaozhi_events_user_id ON xiaozhi_events(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_activity_user_updated ON learning_activity_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_activity_route ON learning_activity_sessions(user_id, route);
CREATE INDEX IF NOT EXISTS idx_learning_feedback_user_updated ON learning_feedback_records(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_feedback_task ON learning_feedback_records(user_id, task_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_feedback_profile ON learning_feedback_records(profile_report_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_xiaozhi_messages_user_id ON xiaozhi_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_multimodal_inputs_user_created ON multimodal_inputs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_xiaozhi_tasks_user_id ON xiaozhi_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_xiaozhi_tasks_task_id ON xiaozhi_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_xiaozhi_tasks_user_type_id ON xiaozhi_tasks(user_id, task_type, id DESC);
CREATE INDEX IF NOT EXISTS idx_generated_video_covers_user_status ON generated_video_covers(user_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_orchestration_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_task_id ON agent_orchestration_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_updated_at ON agent_orchestration_runs(updated_at);
CREATE INDEX IF NOT EXISTS idx_agent_handoffs_run_id ON agent_orchestration_handoffs(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_run_id ON agent_orchestration_events(run_id);
CREATE INDEX IF NOT EXISTS idx_profile_agent_conversations_profile ON profile_agent_conversations(user_id, profile_report_id);
CREATE INDEX IF NOT EXISTS idx_profile_agent_messages_recent ON profile_agent_messages(conversation_id, compacted, sequence DESC);
CREATE INDEX IF NOT EXISTS idx_profile_agent_messages_run ON profile_agent_messages(run_id, sequence);
CREATE INDEX IF NOT EXISTS idx_profile_agent_snapshots_version ON profile_agent_context_snapshots(conversation_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_concepts_user_domain ON knowledge_graph_concepts(user_id, domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_user_source ON knowledge_graph_edges(user_id, source_type, source_key);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_user_target ON knowledge_graph_edges(user_id, target_type, target_key);
CREATE INDEX IF NOT EXISTS idx_knowledge_feedback_user_status ON knowledge_feedback_candidates(user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_feedback_run ON knowledge_feedback_candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_growth_user_time ON knowledge_growth_memories(user_id, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_growth_source ON knowledge_growth_memories(user_id, source_type, source_key);
CREATE INDEX IF NOT EXISTS idx_agent_runtime_settings_updated_at ON user_agent_runtime_settings(updated_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_learning_path_configs_updated_at ON learning_path_configs(updated_at);
CREATE INDEX IF NOT EXISTS idx_user_learning_path_configs_updated_at ON user_learning_path_configs(updated_at);
CREATE INDEX IF NOT EXISTS idx_learning_path_profile_configs_updated_at ON learning_path_profile_configs(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_path_node_caches_user_id ON learning_path_node_caches(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_path_node_caches_updated_at ON learning_path_node_caches(updated_at);
CREATE INDEX IF NOT EXISTS idx_learning_documents_user_updated ON generated_learning_documents(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_documents_profile ON generated_learning_documents(profile_report_id);
CREATE INDEX IF NOT EXISTS idx_effect_assessments_user_created ON learning_effect_assessments(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_effect_assessments_profile ON learning_effect_assessments(profile_report_id);
CREATE INDEX IF NOT EXISTS idx_effect_assessments_run ON learning_effect_assessments(run_id);
CREATE INDEX IF NOT EXISTS idx_private_knowledge_collections_user ON private_knowledge_collections(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_private_knowledge_state_active ON user_private_knowledge_state(active_collection_id);
CREATE INDEX IF NOT EXISTS idx_private_knowledge_documents_collection ON private_knowledge_documents(user_id, collection_id);
CREATE INDEX IF NOT EXISTS idx_private_knowledge_chunks_collection ON private_knowledge_chunks(user_id, collection_id);
CREATE INDEX IF NOT EXISTS idx_private_knowledge_chunks_document ON private_knowledge_chunks(document_id, chunk_index);
"""


QUESTION_GENERATOR_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS question_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    course_name TEXT,
    target_topic TEXT,
    summary TEXT,
    question_count INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS exam_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    sheet_id INTEGER,
    title TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    total_score REAL NOT NULL DEFAULT 100,
    correct_count INTEGER NOT NULL DEFAULT 0,
    question_count INTEGER NOT NULL DEFAULT 0,
    answers_json TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(sheet_id) REFERENCES question_sheets(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_question_configs (
    user_id INTEGER PRIMARY KEY,
    config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


QUESTION_GENERATOR_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_question_sheets_created_at ON question_sheets(created_at);
CREATE INDEX IF NOT EXISTS idx_question_sheets_user_id ON question_sheets(user_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_sheet_id ON exam_results(sheet_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_created_at ON exam_results(created_at);
CREATE INDEX IF NOT EXISTS idx_exam_results_user_id ON exam_results(user_id);
"""


def ensure_columns(conn: sqlite3.Connection, table: str, required_columns: dict[str, str]) -> None:
    existing_columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_definition}")


def migrate_learning_profile_versions(conn: sqlite3.Connection) -> None:
    migration_key = "20260710_learning_profile_versions_v1"
    applied = conn.execute(
        "SELECT 1 FROM system_schema_migrations WHERE migration_key = ?",
        (migration_key,),
    ).fetchone()
    if applied:
        return

    rows = conn.execute(
        """
        SELECT id, user_id, profile_name, version, created_at, updated_at
        FROM learning_profile_reports
        ORDER BY user_id, id
        """
    ).fetchall()
    version_by_user: dict[int, int] = {}
    for row in rows:
        user_id = int(row["user_id"])
        version_by_user[user_id] = version_by_user.get(user_id, 0) + 1
        version = version_by_user[user_id]
        created_at = str(row["created_at"] or "")
        profile_name = str(row["profile_name"] or "").strip()
        if not profile_name or profile_name == "学习画像":
            profile_name = f"学习画像 v{version}"
        conn.execute(
            """
            UPDATE learning_profile_reports
            SET profile_name = ?, version = ?, updated_at = ?, archived = COALESCE(archived, 0)
            WHERE id = ?
            """,
            (profile_name, version, str(row["updated_at"] or created_at), int(row["id"])),
        )

    conn.execute(
        "INSERT INTO system_schema_migrations (migration_key, applied_at) VALUES (?, datetime('now', 'localtime'))",
        (migration_key,),
    )


def backfill_learning_profile_portrait_files(
    conn: sqlite3.Connection,
    portrait_dir: str | Path | None = None,
) -> int:
    """Import legacy profile-<report_id>.png files into SQLite once per report."""
    root = Path(portrait_dir) if portrait_dir is not None else Path(__file__).resolve().parent / "data" / "profile_portraits"
    if not root.is_dir():
        return 0

    migrated = 0
    now = conn.execute("SELECT datetime('now', 'localtime') AS value").fetchone()["value"]
    for image_path in root.glob("profile-*.png"):
        match = re.fullmatch(r"profile-(\d+)\.png", image_path.name)
        if not match:
            continue
        report_id = int(match.group(1))
        report_row = conn.execute(
            "SELECT user_id, report_json FROM learning_profile_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if not report_row:
            continue

        stored = conn.execute(
            "SELECT status, LENGTH(image_blob) AS image_size, source FROM learning_profile_portraits WHERE report_id = ?",
            (report_id,),
        ).fetchone()
        source = str(stored["source"] or "") if stored else ""
        if not stored or stored["status"] != "ready" or int(stored["image_size"] or 0) <= 0:
            image_bytes = image_path.read_bytes()
            if len(image_bytes) < 1024 or not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            source = source or "filesystem-migration"
            conn.execute(
                """
                INSERT INTO learning_profile_portraits
                    (report_id, user_id, image_blob, mime_type, source, status, error, created_at, updated_at)
                VALUES (?, ?, ?, 'image/png', ?, 'ready', '', ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    image_blob = excluded.image_blob,
                    mime_type = excluded.mime_type,
                    source = excluded.source,
                    status = 'ready',
                    error = '',
                    updated_at = excluded.updated_at
                """,
                (report_id, int(report_row["user_id"]), sqlite3.Binary(image_bytes), source, now, now),
            )
            migrated += 1

        try:
            report = json.loads(str(report_row["report_json"] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            report = {}
        if not isinstance(report, dict):
            report = {}
        portrait = report.get("portrait") if isinstance(report.get("portrait"), dict) else {}
        stable_url = f"/api/learning-profile/profiles/{report_id}/portrait"
        if portrait.get("url") != stable_url or portrait.get("status") != "ready":
            report["portrait"] = {
                "url": stable_url,
                "source": str(portrait.get("source") or source or "filesystem-migration"),
                "status": "ready",
            }
            conn.execute(
                "UPDATE learning_profile_reports SET report_json = ? WHERE id = ?",
                (json.dumps(report, ensure_ascii=False), report_id),
            )
    return migrated


def migrate_learning_profile_portraits(conn: sqlite3.Connection) -> None:
    migration_key = "20260711_learning_profile_portraits_v1"
    # Re-scan on every startup so a PNG written just before an interrupted
    # database update is still recovered into the authoritative BLOB store.
    backfill_learning_profile_portrait_files(conn)
    applied = conn.execute(
        "SELECT 1 FROM system_schema_migrations WHERE migration_key = ?",
        (migration_key,),
    ).fetchone()
    if applied:
        return
    conn.execute(
        "INSERT INTO system_schema_migrations (migration_key, applied_at) VALUES (?, datetime('now', 'localtime'))",
        (migration_key,),
    )


def recover_interrupted_learning_profile_portraits(conn: sqlite3.Connection) -> int:
    """Release portrait jobs that cannot survive a backend process restart."""
    updated = conn.execute(
        """
        UPDATE learning_profile_portraits
        SET status = 'missing', error = '', generation_token = '',
            updated_at = datetime('now', 'localtime')
        WHERE status = 'generating'
        """
    )
    return max(0, int(updated.rowcount or 0))


def recover_interrupted_xiaozhi_tasks(conn: sqlite3.Connection) -> int:
    """Fail in-memory background tasks that cannot survive a process restart."""
    task_rows = conn.execute(
        "SELECT task_id FROM xiaozhi_tasks WHERE status IN ('queued', 'running')"
    ).fetchall()
    task_ids = [str(row["task_id"]) for row in task_rows]
    if not task_ids:
        return 0

    placeholders = ",".join("?" for _ in task_ids)
    timestamp_sql = "datetime('now', 'localtime')"
    updated = conn.execute(
        f"""
        UPDATE xiaozhi_tasks
        SET status = 'failed',
            error = CASE
                WHEN TRIM(COALESCE(error, '')) = '' THEN '服务重启导致任务中断，请重新发起'
                ELSE error
            END,
            updated_at = {timestamp_sql}
        WHERE task_id IN ({placeholders})
          AND status IN ('queued', 'running')
        """,
        task_ids,
    )
    conn.execute(
        f"""
        UPDATE agent_orchestration_runs
        SET status = 'failed', updated_at = {timestamp_sql}
        WHERE task_id IN ({placeholders})
          AND status IN ('queued', 'running')
        """,
        task_ids,
    )
    return max(0, int(updated.rowcount or 0))


def init_auth_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(AUTH_SCHEMA_SQL)
    ensure_columns(conn, "users", {"email": "email TEXT", "status": "status TEXT NOT NULL DEFAULT 'enabled'"})
    ensure_columns(
        conn,
        "learning_profile_reports",
        {
            "profile_name": "profile_name TEXT NOT NULL DEFAULT '学习画像'",
            "version": "version INTEGER NOT NULL DEFAULT 1",
            "parent_report_id": "parent_report_id INTEGER",
            "updated_at": "updated_at TEXT NOT NULL DEFAULT ''",
            "archived": "archived INTEGER NOT NULL DEFAULT 0",
        },
    )
    ensure_columns(
        conn,
        "learning_profile_portraits",
        {
            "generation_token": "generation_token TEXT NOT NULL DEFAULT ''",
            "attempt_count": "attempt_count INTEGER NOT NULL DEFAULT 0",
        },
    )
    ensure_columns(
        conn,
        "agent_orchestration_runs",
        {
            "harness_name": "harness_name TEXT NOT NULL DEFAULT ''",
            "harness_version": "harness_version TEXT NOT NULL DEFAULT ''",
            "skill_id": "skill_id TEXT NOT NULL DEFAULT ''",
            "mcp_server": "mcp_server TEXT NOT NULL DEFAULT ''",
            "mcp_tool": "mcp_tool TEXT NOT NULL DEFAULT ''",
            "policy_json": "policy_json TEXT NOT NULL DEFAULT '{}'",
            "profile_report_id": "profile_report_id INTEGER NOT NULL DEFAULT 0",
        },
    )
    ensure_columns(
        conn,
        "xiaozhi_tasks",
        {"profile_report_id": "profile_report_id INTEGER NOT NULL DEFAULT 0"},
    )
    ensure_columns(
        conn,
        "xiaozhi_messages",
        {"profile_report_id": "profile_report_id INTEGER NOT NULL DEFAULT 0"},
    )
    conn.execute(
        """
        UPDATE xiaozhi_messages AS chat
        SET profile_report_id = COALESCE(
            (
                SELECT conversation.profile_report_id
                FROM profile_agent_messages AS message
                JOIN profile_agent_conversations AS conversation
                  ON conversation.id = message.conversation_id
                WHERE message.dedupe_key IN (
                    'chat:user:' || chat.id,
                    'chat:assistant:' || chat.id
                )
                  AND conversation.user_id = chat.user_id
                ORDER BY message.id DESC LIMIT 1
            ),
            0
        )
        WHERE chat.profile_report_id = 0
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_xiaozhi_messages_user_profile_id "
        "ON xiaozhi_messages(user_id, profile_report_id, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_xiaozhi_tasks_user_profile_id "
        "ON xiaozhi_tasks(user_id, profile_report_id, id DESC)"
    )
    conn.execute(
        """
        UPDATE xiaozhi_tasks AS task
        SET profile_report_id = COALESCE(
            (
                SELECT NULLIF(run.profile_report_id, 0)
                FROM agent_orchestration_runs AS run
                WHERE run.task_id = task.task_id AND run.user_id = task.user_id
                ORDER BY run.id DESC LIMIT 1
            ),
            (
                SELECT conversation.profile_report_id
                FROM profile_agent_messages AS message
                JOIN profile_agent_conversations AS conversation
                  ON conversation.id = message.conversation_id
                WHERE message.task_id = task.task_id AND conversation.user_id = task.user_id
                ORDER BY message.id DESC LIMIT 1
            ),
            0
        )
        WHERE task.profile_report_id = 0
        """
    )
    ensure_columns(
        conn,
        "learning_activity_sessions",
        {
            "status": "status TEXT NOT NULL DEFAULT 'active'",
            "ended_at": "ended_at TEXT NOT NULL DEFAULT ''",
        },
    )
    migrate_learning_profile_versions(conn)
    migrate_learning_profile_portraits(conn)
    conn.executescript(AUTH_INDEX_SQL)


def init_question_generator_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(QUESTION_GENERATOR_SCHEMA_SQL)
    ensure_columns(conn, "question_sheets", {"user_id": "user_id INTEGER NOT NULL DEFAULT 0"})
    ensure_columns(conn, "exam_results", {"user_id": "user_id INTEGER NOT NULL DEFAULT 0"})
    conn.executescript(QUESTION_GENERATOR_INDEX_SQL)
