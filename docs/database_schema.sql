CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    login_id TEXT UNIQUE,
    user_type TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT,
    display_name TEXT,
    teacher TEXT,
    email TEXT,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_type, username)
);

CREATE TABLE teacher_student_links (
    teacher_username TEXT NOT NULL,
    student_username TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    teacher_user_id INTEGER,
    student_user_id INTEGER,
    PRIMARY KEY (teacher_username, student_username)
);

CREATE TABLE twin_profiles (
    username TEXT PRIMARY KEY,
    user_id INTEGER,
    last_updated TEXT,
    overall_mastery REAL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE twin_profile_nodes (
    username TEXT NOT NULL,
    user_id INTEGER,
    node_id TEXT NOT NULL,
    node_path_json TEXT,
    quiz_score REAL,
    progress REAL DEFAULT 0,
    study_duration_minutes REAL DEFAULT 0,
    llm_interaction_count INTEGER DEFAULT 0,
    mastery_score REAL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (username, node_id)
);

CREATE TABLE twin_history (
    username TEXT NOT NULL,
    user_id INTEGER,
    snapshot_date TEXT NOT NULL,
    overall_mastery REAL DEFAULT 0,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (username, snapshot_date)
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER,
    username TEXT NOT NULL,
    user_type TEXT NOT NULL,
    created_at TEXT,
    last_accessed TEXT,
    current_pdf_path TEXT,
    current_node TEXT,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE user_states (
    username TEXT PRIMARY KEY,
    user_id INTEGER,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE llm_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    username TEXT,
    user_id INTEGER,
    module TEXT,
    model TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE learning_plans (
    username TEXT NOT NULL,
    user_id INTEGER,
    filename TEXT NOT NULL,
    plan_path TEXT,
    category TEXT,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (username, filename)
);

CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    course_name TEXT,
    source_path TEXT,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE course_nodes (
    course_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_name TEXT,
    node_path_json TEXT,
    depth INTEGER DEFAULT 0,
    parent_node_id TEXT,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (course_id, node_id)
);

CREATE TABLE resources (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    resource_path TEXT NOT NULL,
    resource_type TEXT,
    title TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (course_id, node_id, resource_path)
);

CREATE TABLE quiz_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    course_id TEXT,
    node_id TEXT,
    score REAL,
    total REAL,
    passed INTEGER DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_users_type ON users(user_type);
CREATE UNIQUE INDEX idx_users_user_id ON users(user_id);
CREATE UNIQUE INDEX idx_users_login_id ON users(login_id);

CREATE INDEX idx_links_teacher_user_id ON teacher_student_links(teacher_user_id);
CREATE INDEX idx_links_student_user_id ON teacher_student_links(student_user_id);

CREATE INDEX idx_twin_profiles_user_id ON twin_profiles(user_id);
CREATE INDEX idx_twin_nodes_user_id ON twin_profile_nodes(user_id);
CREATE INDEX idx_twin_nodes_username ON twin_profile_nodes(username);
CREATE INDEX idx_twin_history_user_id ON twin_history(user_id);

CREATE INDEX idx_sessions_username ON sessions(username);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

CREATE INDEX idx_logs_username ON llm_logs(username);
CREATE INDEX idx_logs_timestamp ON llm_logs(timestamp);
CREATE INDEX idx_llm_logs_user_id ON llm_logs(user_id);

CREATE INDEX idx_plans_username ON learning_plans(username);
CREATE INDEX idx_learning_plans_user_id ON learning_plans(user_id);

CREATE INDEX idx_user_states_user_id ON user_states(user_id);

CREATE INDEX idx_course_nodes_course ON course_nodes(course_id);
CREATE INDEX idx_resources_course_node ON resources(course_id, node_id);
CREATE INDEX idx_resources_path ON resources(resource_path);

CREATE INDEX idx_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX idx_quiz_attempts_username ON quiz_attempts(username);
CREATE INDEX idx_quiz_attempts_course_id ON quiz_attempts(course_id);
CREATE INDEX idx_quiz_attempts_created_at ON quiz_attempts(created_at);
