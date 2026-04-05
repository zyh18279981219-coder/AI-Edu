CREATE INDEX idx_logs_timestamp ON llm_logs(timestamp)

CREATE INDEX idx_logs_username ON llm_logs(username)

CREATE INDEX idx_plans_username ON learning_plans(username)

CREATE INDEX idx_sessions_username ON sessions(username)

CREATE INDEX idx_users_type ON users(user_type)

CREATE TABLE learning_plans (
                    username TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    plan_path TEXT,
                    category TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, filename)
                )

CREATE TABLE llm_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    username TEXT,
                    module TEXT,
                    model TEXT,
                    payload_json TEXT NOT NULL
                )

CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    user_type TEXT NOT NULL,
                    created_at TEXT,
                    last_accessed TEXT,
                    current_pdf_path TEXT,
                    current_node TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )

CREATE TABLE sqlite_sequence(name,seq)

CREATE TABLE teacher_student_links (
                    teacher_username TEXT NOT NULL,
                    student_username TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (teacher_username, student_username)
                )

CREATE TABLE twin_history (
                    username TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    overall_mastery REAL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, snapshot_date)
                )

CREATE TABLE twin_profiles (
                    username TEXT PRIMARY KEY,
                    last_updated TEXT,
                    overall_mastery REAL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )

CREATE TABLE user_states (
                    username TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )

CREATE TABLE users (
                    user_type TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT,
                    display_name TEXT,
                    teacher TEXT,
                    email TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_type, username)
                )