from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class SQLiteStore:
    def __init__(self, db_path: str | Path = "data/app.db"):
        project_root = Path(__file__).resolve().parent.parent
        resolved = Path(db_path)
        if not resolved.is_absolute():
            resolved = project_root / resolved
        self.db_path = resolved
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._source_log_path = Path("data/Log/data_source_audit.log")
        self._source_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self):
        with self._lock, self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
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

                CREATE TABLE IF NOT EXISTS teacher_student_links (
                    teacher_username TEXT NOT NULL,
                    student_username TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (teacher_username, student_username)
                );

                CREATE TABLE IF NOT EXISTS twin_profiles (
                    username TEXT PRIMARY KEY,
                    user_id INTEGER,
                    last_updated TEXT,
                    overall_mastery REAL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS twin_history (
                    username TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    overall_mastery REAL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, snapshot_date)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    user_type TEXT NOT NULL,
                    created_at TEXT,
                    last_accessed TEXT,
                    current_pdf_path TEXT,
                    current_node TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_states (
                    username TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS llm_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    username TEXT,
                    module TEXT,
                    model TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS learning_plans (
                    username TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    plan_path TEXT,
                    category TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, filename)
                );

                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT,
                    source_path TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS course_nodes (
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

                CREATE TABLE IF NOT EXISTS resources (
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

                CREATE TABLE IF NOT EXISTS quiz_attempts (
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

                CREATE TABLE IF NOT EXISTS twin_profile_nodes (
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

                CREATE INDEX IF NOT EXISTS idx_users_type ON users(user_type);
                CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username);
                CREATE INDEX IF NOT EXISTS idx_logs_username ON llm_logs(username);
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON llm_logs(timestamp);
                CREATE INDEX IF NOT EXISTS idx_plans_username ON learning_plans(username);
                CREATE INDEX IF NOT EXISTS idx_twin_nodes_user_id ON twin_profile_nodes(user_id);
                CREATE INDEX IF NOT EXISTS idx_twin_nodes_username ON twin_profile_nodes(username);
                CREATE INDEX IF NOT EXISTS idx_course_nodes_course ON course_nodes(course_id);
                CREATE INDEX IF NOT EXISTS idx_resources_course_node ON resources(course_id, node_id);
                CREATE INDEX IF NOT EXISTS idx_resources_path ON resources(resource_path);
                CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id ON quiz_attempts(user_id);
                CREATE INDEX IF NOT EXISTS idx_quiz_attempts_username ON quiz_attempts(username);
                CREATE INDEX IF NOT EXISTS idx_quiz_attempts_course_id ON quiz_attempts(course_id);
                CREATE INDEX IF NOT EXISTS idx_quiz_attempts_created_at ON quiz_attempts(created_at);
                """
            )
            self._ensure_schema_upgrades(conn)

    def _column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(str(row["name"]) == column for row in rows)

    def _ensure_column(self, conn: sqlite3.Connection, table: str, definition: str) -> None:
        column_name = definition.split()[0]
        if self._column_exists(conn, table, column_name):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

    def _ensure_schema_upgrades(self, conn: sqlite3.Connection) -> None:
        # users table: ensure stable identity fields first.
        self._ensure_column(conn, "users", "user_id INTEGER")
        self._ensure_column(conn, "users", "login_id TEXT")
        conn.execute(
            """
            UPDATE users
            SET user_id = rowid
            WHERE user_id IS NULL
            """
        )
        conn.execute(
            """
            UPDATE users
            SET login_id = lower(substr(user_type, 1, 3)) || printf('%06d', user_id)
            WHERE (login_id IS NULL OR trim(login_id) = '') AND user_id IS NOT NULL
            """
        )

        # users table: migrate physical PK from (user_type, username) to user_id.
        users_pk_cols = [
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
            if int(row["pk"] or 0) > 0
        ]
        users_pk_is_user_id = users_pk_cols == ["user_id"]
        if not users_pk_is_user_id:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users_new (
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
                )
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO users_new
                (user_id, login_id, user_type, username, password, display_name, teacher, email, payload_json, updated_at)
                SELECT
                    user_id,
                    login_id,
                    user_type,
                    username,
                    password,
                    display_name,
                    teacher,
                    email,
                    payload_json,
                    updated_at
                FROM users
                """
            )
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")

        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_login_id ON users(login_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_type ON users(user_type)")

        # relation tables: add id-based columns for forward migration.
        self._ensure_column(conn, "teacher_student_links", "teacher_user_id INTEGER")
        self._ensure_column(conn, "teacher_student_links", "student_user_id INTEGER")
        conn.execute(
            """
            UPDATE teacher_student_links
            SET teacher_user_id = (
                SELECT u.user_id FROM users u
                WHERE u.user_type = 'teacher' AND u.username = teacher_student_links.teacher_username
                LIMIT 1
            )
            WHERE teacher_user_id IS NULL
            """
        )
        conn.execute(
            """
            UPDATE teacher_student_links
            SET student_user_id = (
                SELECT u.user_id FROM users u
                WHERE u.user_type = 'student' AND u.username = teacher_student_links.student_username
                LIMIT 1
            )
            WHERE student_user_id IS NULL
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_teacher_user_id ON teacher_student_links(teacher_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_student_user_id ON teacher_student_links(student_user_id)")

        # twin/session tables: add user_id for id-based joins.
        self._ensure_column(conn, "twin_profiles", "user_id INTEGER")
        self._ensure_column(conn, "twin_history", "user_id INTEGER")
        self._ensure_column(conn, "sessions", "user_id INTEGER")
        self._ensure_column(conn, "learning_plans", "user_id INTEGER")
        self._ensure_column(conn, "user_states", "user_id INTEGER")
        self._ensure_column(conn, "llm_logs", "user_id INTEGER")

        for table, user_type in [
            ("twin_profiles", "student"),
            ("twin_history", "student"),
            ("sessions", None),
            ("learning_plans", None),
            ("user_states", None),
            ("llm_logs", None),
        ]:
            if user_type is None:
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET user_id = (
                        SELECT u.user_id FROM users u
                        WHERE u.username = {table}.username
                        ORDER BY CASE u.user_type WHEN 'student' THEN 0 WHEN 'teacher' THEN 1 ELSE 2 END
                        LIMIT 1
                    )
                    WHERE user_id IS NULL
                    """
                )
            else:
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET user_id = (
                        SELECT u.user_id FROM users u
                        WHERE u.username = {table}.username AND u.user_type = ?
                        LIMIT 1
                    )
                    WHERE user_id IS NULL
                    """,
                    (user_type,),
                )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_twin_profiles_user_id ON twin_profiles(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_twin_history_user_id ON twin_history(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_learning_plans_user_id ON learning_plans(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_states_user_id ON user_states(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_user_id ON llm_logs(user_id)")

        # drop legacy payload_json from twin_profiles after node-detail migration.
        twin_profile_cols = [str(row["name"]) for row in conn.execute("PRAGMA table_info(twin_profiles)").fetchall()]
        if "payload_json" in twin_profile_cols:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS twin_profiles_new (
                    username TEXT PRIMARY KEY,
                    user_id INTEGER,
                    last_updated TEXT,
                    overall_mastery REAL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO twin_profiles_new (username, user_id, last_updated, overall_mastery, updated_at)
                SELECT username, user_id, last_updated, overall_mastery, updated_at
                FROM twin_profiles
                """
            )
            conn.execute("DROP TABLE twin_profiles")
            conn.execute("ALTER TABLE twin_profiles_new RENAME TO twin_profiles")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_twin_profiles_user_id ON twin_profiles(user_id)")

    def _json(self, payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _audit_source(self, event: str, **payload: Any) -> None:
        fields = " ".join([f"{key}={payload[key]}" for key in sorted(payload.keys())])
        line = f"{self._now()} event={event} {fields}".strip()
        try:
            with self._source_log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            logger.exception("failed writing source audit log")

    def _replace_twin_profile_nodes(
        self,
        conn: sqlite3.Connection,
        username: str,
        user_id: Optional[int],
        payload: Dict[str, Any],
    ) -> None:
        nodes = payload.get("knowledge_nodes") if isinstance(payload, dict) else None
        if not isinstance(nodes, list):
            nodes = []

        conn.execute("DELETE FROM twin_profile_nodes WHERE username = ?", (username,))
        timestamp = self._now()
        for item in nodes:
            if not isinstance(item, dict):
                continue
            node_id = str(item.get("node_id") or "").strip()
            if not node_id:
                continue
            node_path = item.get("node_path")
            if not isinstance(node_path, list):
                node_path = []
            quiz_score = item.get("quiz_score")
            try:
                quiz_score = float(quiz_score) if quiz_score is not None else None
            except (TypeError, ValueError):
                quiz_score = None
            try:
                progress = float(item.get("progress", 0) or 0)
            except (TypeError, ValueError):
                progress = 0.0
            try:
                study_duration = float(item.get("study_duration_minutes", 0) or 0)
            except (TypeError, ValueError):
                study_duration = 0.0
            try:
                llm_count = int(item.get("llm_interaction_count", 0) or 0)
            except (TypeError, ValueError):
                llm_count = 0
            try:
                mastery_score = float(item.get("mastery_score", 0) or 0)
            except (TypeError, ValueError):
                mastery_score = 0.0

            conn.execute(
                """
                INSERT OR REPLACE INTO twin_profile_nodes
                (
                    username,
                    user_id,
                    node_id,
                    node_path_json,
                    quiz_score,
                    progress,
                    study_duration_minutes,
                    llm_interaction_count,
                    mastery_score,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    user_id,
                    node_id,
                    self._json(node_path),
                    quiz_score,
                    progress,
                    study_duration,
                    llm_count,
                    mastery_score,
                    timestamp,
                ),
            )

    def list_users(self, user_type: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                "SELECT user_id, login_id, payload_json FROM users WHERE user_type = ? ORDER BY username",
                (user_type,),
            ).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = json.loads(row["payload_json"])
            if isinstance(item, dict):
                item.setdefault("user_id", row["user_id"])
                item.setdefault("login_id", row["login_id"])
            result.append(item)
        return result

    def get_user(self, user_type: str, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT user_id, login_id, payload_json FROM users WHERE user_type = ? AND username = ?",
                (user_type, username),
            ).fetchone()
        if not row:
            return None
        item = json.loads(row["payload_json"])
        if isinstance(item, dict):
            item.setdefault("user_id", row["user_id"])
            item.setdefault("login_id", row["login_id"])
        return item

    def get_user_by_identifier(self, user_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        identifier = str(identifier or "").strip()
        if not identifier:
            return None

        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT user_id, login_id, payload_json
                FROM users
                WHERE user_type = ?
                  AND (
                    login_id = ?
                    OR CAST(user_id AS TEXT) = ?
                  )
                ORDER BY CASE
                    WHEN login_id = ? THEN 0
                    ELSE 1
                END
                LIMIT 1
                """,
                (user_type, identifier, identifier, identifier),
            ).fetchone()
        if not row:
            logger.info("data-source: users miss user_type=%s identifier=%s", user_type, identifier)
            self._audit_source("users_miss", user_type=user_type, identifier=identifier)
            return None
        item = json.loads(row["payload_json"])
        if isinstance(item, dict):
            item.setdefault("user_id", row["user_id"])
            item.setdefault("login_id", row["login_id"])
        logger.info(
            "data-source: users hit user_type=%s identifier=%s user_id=%s login_id=%s",
            user_type,
            identifier,
            row["user_id"],
            row["login_id"],
        )
        self._audit_source(
            "users_hit",
            user_type=user_type,
            identifier=identifier,
            user_id=row["user_id"],
            login_id=row["login_id"],
        )
        return item

    def get_user_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT user_id, login_id, payload_json FROM users WHERE user_id = ? LIMIT 1",
                (int(user_id),),
            ).fetchone()
        if not row:
            return None
        item = json.loads(row["payload_json"])
        if isinstance(item, dict):
            item.setdefault("user_id", row["user_id"])
            item.setdefault("login_id", row["login_id"])
        return item

    def resolve_user_identity(self, user_type: str, identifier: str) -> Dict[str, Any]:
        user = self.get_user_by_identifier(user_type, identifier)
        if user:
            return {
                "username": user.get("username"),
                "user_id": user.get("user_id"),
                "login_id": user.get("login_id"),
            }
        return {
            "username": None,
            "user_id": None,
            "login_id": None,
        }

    def list_teacher_students(self, teacher_identifier: str) -> List[Dict[str, Any]]:
        teacher = self.get_user_by_identifier("teacher", teacher_identifier)
        teacher_user_id = teacher.get("user_id") if teacher else None
        if teacher_user_id is None:
            logger.info("data-source: teacher_student_links miss teacher_identifier=%s", teacher_identifier)
            self._audit_source("teacher_students_miss", teacher_identifier=teacher_identifier)
            return []
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    l.teacher_username,
                    l.teacher_user_id,
                    l.student_username,
                    l.student_user_id,
                    l.updated_at,
                    u.login_id AS student_login_id,
                    u.payload_json AS student_payload_json
                FROM teacher_student_links l
                LEFT JOIN users u
                    ON u.user_type = 'student'
                    AND l.student_user_id = u.user_id
                WHERE l.teacher_user_id = ?
                  AND l.student_user_id IS NOT NULL
                ORDER BY l.student_username
                """,
                (teacher_user_id,),
            ).fetchall()
        logger.info(
            "data-source: teacher_student_links hit teacher_identifier=%s teacher_user_id=%s rows=%s",
            teacher_identifier,
            teacher_user_id,
            len(rows),
        )
        self._audit_source(
            "teacher_students_hit",
            teacher_identifier=teacher_identifier,
            teacher_user_id=teacher_user_id,
            rows=len(rows),
        )
        result: List[Dict[str, Any]] = []
        for row in rows:
            payload = {}
            raw = row["student_payload_json"]
            if raw:
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {}
            result.append(
                {
                    "teacher_username": row["teacher_username"],
                    "teacher_user_id": row["teacher_user_id"],
                    "student_username": row["student_username"],
                    "student_user_id": row["student_user_id"],
                    "student_login_id": row["student_login_id"],
                    "updated_at": row["updated_at"],
                    "student_payload": payload,
                }
            )
        return result

    def replace_users(self, user_type: str, users: Iterable[Dict[str, Any]]) -> None:
        users = list(users)
        timestamp = self._now()
        with self._lock, self.connection() as conn:
            existing_rows = conn.execute(
                "SELECT username, user_id, login_id FROM users WHERE user_type = ?",
                (user_type,),
            ).fetchall()
            existing_map = {
                str(row["username"]): {"user_id": row["user_id"], "login_id": row["login_id"]}
                for row in existing_rows
            }
            current_max = conn.execute("SELECT COALESCE(MAX(user_id), 0) FROM users").fetchone()[0] or 0

            conn.execute("DELETE FROM users WHERE user_type = ?", (user_type,))
            if user_type == "teacher":
                conn.execute("DELETE FROM teacher_student_links")
            for user in users:
                username = user.get("username")
                if not username:
                    continue
                existing_identity = existing_map.get(str(username), {})
                user_id = user.get("user_id") or existing_identity.get("user_id")
                if user_id is None:
                    current_max += 1
                    user_id = current_max
                login_id = str(user.get("login_id") or existing_identity.get("login_id") or "").strip()
                if not login_id:
                    login_id = f"{str(user_type)[:3].lower()}{int(user_id):06d}"
                display_name = user.get("stu_name") or user.get("name") or username
                user = dict(user)
                user["user_id"] = int(user_id)
                user["login_id"] = login_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO users
                    (user_id, login_id, user_type, username, password, display_name, teacher, email, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(user_id),
                        login_id,
                        user_type,
                        username,
                        user.get("password"),
                        display_name,
                        user.get("teacher"),
                        user.get("email"),
                        self._json(user),
                        timestamp,
                    ),
                )
                if user_type == "teacher":
                    for student_username in user.get("students", []) or []:
                        student_row = conn.execute(
                            "SELECT user_id FROM users WHERE user_type = 'student' AND username = ? LIMIT 1",
                            (student_username,),
                        ).fetchone()
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO teacher_student_links
                            (teacher_username, student_username, teacher_user_id, student_user_id, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (username, student_username, int(user_id), student_row["user_id"] if student_row else None, timestamp),
                        )

    def save_twin_profile(self, username: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            user_row = conn.execute(
                "SELECT user_id FROM users WHERE user_type = 'student' AND username = ? LIMIT 1",
                (username,),
            ).fetchone()
            user_id = int(payload.get("user_id")) if payload.get("user_id") is not None else (user_row["user_id"] if user_row else None)
            conn.execute(
                """
                INSERT OR REPLACE INTO twin_profiles
                (username, user_id, last_updated, overall_mastery, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    user_id,
                    payload.get("last_updated"),
                    payload.get("overall_mastery", 0),
                    self._now(),
                ),
            )
            self._replace_twin_profile_nodes(conn, username=username, user_id=user_id, payload=payload)

    def get_twin_profile(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT username, user_id, last_updated, overall_mastery FROM twin_profiles WHERE username = ?",
                (username,),
            ).fetchone()
        if not row:
            self._audit_source("twin_profile_miss", username=username)
            return None
        nodes = self._load_twin_nodes_for_usernames([str(row["username"])])
        node_count = len(nodes.get(str(row["username"]), []))
        self._audit_source(
            "twin_profile_hit",
            username=row["username"],
            user_id=row["user_id"],
            node_count=node_count,
            source="twin_profiles+twin_profile_nodes",
        )
        return {
            "username": row["username"],
            "user_id": row["user_id"],
            "last_updated": row["last_updated"],
            "overall_mastery": float(row["overall_mastery"] or 0),
            "knowledge_nodes": nodes.get(str(row["username"]), []),
        }

    def list_twin_profiles(self) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                "SELECT username, user_id, last_updated, overall_mastery FROM twin_profiles ORDER BY username"
            ).fetchall()
        usernames = [str(row["username"]) for row in rows]
        nodes_map = self._load_twin_nodes_for_usernames(usernames)
        self._audit_source(
            "twin_profile_list",
            row_count=len(rows),
            source="twin_profiles+twin_profile_nodes",
        )
        return [
            {
                "username": row["username"],
                "user_id": row["user_id"],
                "last_updated": row["last_updated"],
                "overall_mastery": float(row["overall_mastery"] or 0),
                "knowledge_nodes": nodes_map.get(str(row["username"]), []),
            }
            for row in rows
        ]

    def _load_twin_nodes_for_usernames(self, usernames: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        if not usernames:
            return {}
        placeholders = ", ".join(["?"] * len(usernames))
        sql = f"""
            SELECT username, node_id, node_path_json, quiz_score, progress, study_duration_minutes, llm_interaction_count, mastery_score
            FROM twin_profile_nodes
            WHERE username IN ({placeholders})
            ORDER BY username, node_id
        """
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(usernames)).fetchall()
        result: Dict[str, List[Dict[str, Any]]] = {name: [] for name in usernames}
        for row in rows:
            node_path = []
            raw_path = row["node_path_json"]
            if raw_path:
                try:
                    parsed = json.loads(raw_path)
                    if isinstance(parsed, list):
                        node_path = parsed
                except Exception:
                    node_path = []
            result.setdefault(str(row["username"]), []).append(
                {
                    "node_id": row["node_id"],
                    "node_path": node_path,
                    "quiz_score": float(row["quiz_score"]) if row["quiz_score"] is not None else None,
                    "progress": float(row["progress"] or 0),
                    "study_duration_minutes": float(row["study_duration_minutes"] or 0),
                    "llm_interaction_count": int(row["llm_interaction_count"] or 0),
                    "mastery_score": float(row["mastery_score"] or 0),
                }
            )
        return result

    def save_twin_history(self, username: str, snapshot_date: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            user_row = conn.execute(
                "SELECT user_id FROM users WHERE user_type = 'student' AND username = ? LIMIT 1",
                (username,),
            ).fetchone()
            user_id = user_row["user_id"] if user_row else None
            conn.execute(
                """
                INSERT OR REPLACE INTO twin_history
                (username, user_id, snapshot_date, overall_mastery, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    user_id,
                    snapshot_date,
                    payload.get("overall_mastery", 0),
                    self._json(payload),
                    self._now(),
                ),
            )

    def get_twin_history(self, username: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM twin_history
                WHERE username = ?
                ORDER BY snapshot_date
                """,
                (username,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            user_id = payload.get("user_id")
            if user_id is None and payload.get("username"):
                row = conn.execute(
                    """
                    SELECT user_id FROM users
                    WHERE username = ? AND user_type = ?
                    LIMIT 1
                    """,
                    (payload.get("username"), payload.get("user_type")),
                ).fetchone()
                user_id = row["user_id"] if row else None
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, user_id, username, user_type, created_at, last_accessed, current_pdf_path, current_node, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    payload.get("username"),
                    payload.get("user_type"),
                    payload.get("created_at"),
                    payload.get("last_accessed"),
                    payload.get("current_pdf_path"),
                    payload.get("current_node"),
                    self._json(payload),
                    self._now(),
                ),
            )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def delete_session(self, session_id: str) -> None:
        with self._lock, self.connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute("SELECT payload_json FROM sessions").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_sessions_for_user(self, user_type: str, user_identifier: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        identity = self.resolve_user_identity(user_type, user_identifier)
        user_id = identity.get("user_id")
        if user_id is None:
            logger.info("data-source: sessions miss user_type=%s identifier=%s", user_type, user_identifier)
            self._audit_source("sessions_miss", user_type=user_type, identifier=user_identifier)
            return []
        sql = "SELECT payload_json FROM sessions WHERE user_type = ? AND user_id = ? ORDER BY updated_at DESC"
        params: list[Any] = [user_type, user_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        logger.info(
            "data-source: sessions hit user_type=%s identifier=%s user_id=%s rows=%s",
            user_type,
            user_identifier,
            user_id,
            len(rows),
        )
        self._audit_source(
            "sessions_hit",
            user_type=user_type,
            identifier=user_identifier,
            user_id=user_id,
            rows=len(rows),
        )
        return [json.loads(row["payload_json"]) for row in rows]

    def save_user_state(self, username: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            user_id = payload.get("user_id")
            if user_id is None:
                row = conn.execute(
                    """
                    SELECT user_id FROM users
                    WHERE username = ?
                    ORDER BY CASE user_type WHEN 'student' THEN 0 WHEN 'teacher' THEN 1 ELSE 2 END
                    LIMIT 1
                    """,
                    (username,),
                ).fetchone()
                user_id = row["user_id"] if row else None
            conn.execute(
                """
                INSERT OR REPLACE INTO user_states
                (username, user_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, user_id, self._json(payload), self._now()),
            )

    def get_user_state(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM user_states WHERE username = ?",
                (username,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def append_llm_log(self, payload: Dict[str, Any]) -> None:
        request = payload.get("request") or {}
        with self._lock, self.connection() as conn:
            user_id = payload.get("user_id")
            if user_id is None and payload.get("username"):
                row = conn.execute(
                    """
                    SELECT user_id FROM users
                    WHERE username = ?
                    ORDER BY CASE user_type WHEN 'student' THEN 0 WHEN 'teacher' THEN 1 ELSE 2 END
                    LIMIT 1
                    """,
                    (payload.get("username"),),
                ).fetchone()
                user_id = row["user_id"] if row else None
            conn.execute(
                """
                INSERT INTO llm_logs (timestamp, username, user_id, module, model, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("timestamp"),
                    payload.get("username"),
                    user_id,
                    payload.get("module"),
                    request.get("model"),
                    self._json(payload),
                ),
            )

    def replace_llm_logs(self, logs: Iterable[Dict[str, Any]]) -> None:
        with self._lock, self.connection() as conn:
            conn.execute("DELETE FROM llm_logs")
        for item in logs:
            self.append_llm_log(item)

    def list_llm_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT payload_json FROM llm_logs ORDER BY id DESC"
        params: tuple[Any, ...] = ()
        if limit:
            sql += " LIMIT ?"
            params = (limit,)
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_llm_logs_for_user(
        self,
        user_identifier: str,
        user_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if user_type is None:
            logger.info("data-source: llm_logs invalid query missing user_type identifier=%s", user_identifier)
            self._audit_source("llm_logs_invalid", identifier=user_identifier)
            return []
        identity = self.resolve_user_identity(user_type, user_identifier)
        user_id = identity.get("user_id")
        if user_id is None:
            logger.info("data-source: llm_logs miss user_type=%s identifier=%s", user_type, user_identifier)
            self._audit_source("llm_logs_miss", user_type=user_type, identifier=user_identifier)
            return []
        sql = "SELECT payload_json FROM llm_logs WHERE user_id = ? ORDER BY id DESC"
        params: list[Any] = [user_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        logger.info(
            "data-source: llm_logs hit user_type=%s identifier=%s user_id=%s rows=%s",
            user_type,
            user_identifier,
            user_id,
            len(rows),
        )
        self._audit_source(
            "llm_logs_hit",
            user_type=user_type,
            identifier=user_identifier,
            user_id=user_id,
            rows=len(rows),
        )
        return [json.loads(row["payload_json"]) for row in rows]

    def save_learning_plan(
        self,
        username: str,
        filename: str,
        payload: Any,
        plan_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT user_id FROM users
                WHERE username = ?
                ORDER BY CASE user_type WHEN 'student' THEN 0 WHEN 'teacher' THEN 1 ELSE 2 END
                LIMIT 1
                """,
                (username,),
            ).fetchone()
            user_id = row["user_id"] if row else None
            conn.execute(
                """
                INSERT OR REPLACE INTO learning_plans
                (username, user_id, filename, plan_path, category, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    user_id,
                    filename,
                    plan_path,
                    category,
                    self._json(payload),
                    self._now(),
                ),
            )

    def list_learning_plans(
        self,
        username: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT username, filename, plan_path, category, payload_json, updated_at
            FROM learning_plans
        """
        clauses: list[str] = []
        params: list[Any] = []
        if username:
            clauses.append("username = ?")
            params.append(username)
        if categories:
            category_list = [item for item in categories if item]
            if category_list:
                placeholders = ", ".join(["?"] * len(category_list))
                clauses.append(f"category IN ({placeholders})")
                params.extend(category_list)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, filename DESC"
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "username": row["username"],
                "filename": row["filename"],
                "path": row["plan_path"] or "",
                "category": row["category"] or "",
                "data": json.loads(row["payload_json"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def list_learning_plans_by_user_identifier(
        self,
        user_identifier: str,
        user_type: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        if user_type is None:
            logger.info("data-source: learning_plans invalid query missing user_type identifier=%s", user_identifier)
            self._audit_source("learning_plans_invalid", identifier=user_identifier)
            return []
        identity = self.resolve_user_identity(user_type, user_identifier)
        sql = """
            SELECT username, filename, plan_path, category, payload_json, updated_at
            FROM learning_plans
        """
        clauses: list[str] = []
        params: list[Any] = []
        user_id = identity.get("user_id")
        if user_id is None:
            logger.info("data-source: learning_plans miss user_type=%s identifier=%s", user_type, user_identifier)
            self._audit_source("learning_plans_miss", user_type=user_type, identifier=user_identifier)
            return []
        clauses.append("user_id = ?")
        params.append(user_id)
        if categories:
            category_list = [item for item in categories if item]
            if category_list:
                placeholders = ", ".join(["?"] * len(category_list))
                clauses.append(f"category IN ({placeholders})")
                params.extend(category_list)
        sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, filename DESC"
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        logger.info(
            "data-source: learning_plans hit user_type=%s identifier=%s user_id=%s rows=%s",
            user_type,
            user_identifier,
            user_id,
            len(rows),
        )
        self._audit_source(
            "learning_plans_hit",
            user_type=user_type,
            identifier=user_identifier,
            user_id=user_id,
            rows=len(rows),
        )
        return [
            {
                "username": row["username"],
                "filename": row["filename"],
                "path": row["plan_path"] or "",
                "category": row["category"] or "",
                "data": json.loads(row["payload_json"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def get_latest_learning_plan(
        self,
        username: str,
        category: Optional[str] = None,
        filename_prefix: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT username, filename, plan_path, category, payload_json, updated_at
            FROM learning_plans
            WHERE username = ?
        """
        params: list[Any] = [username]
        if category is not None:
            sql += " AND category = ?"
            params.append(category)
        if filename_prefix is not None:
            sql += " AND filename LIKE ?"
            params.append(f"{filename_prefix}%")
        sql += " ORDER BY updated_at DESC, filename DESC LIMIT 1"

        with self._lock, self.connection() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
        if row is None:
            return None
        return {
            "username": row["username"],
            "filename": row["filename"],
            "path": row["plan_path"] or "",
            "category": row["category"] or "",
            "data": json.loads(row["payload_json"]),
            "updated_at": row["updated_at"],
        }

    def _iter_graph_children(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        for key in ("children", "grandchildren", "great-grandchildren"):
            children = node.get(key)
            if isinstance(children, list):
                return [item for item in children if isinstance(item, dict)]
        return []

    def sync_course_from_graph(
        self,
        course_id: str,
        graph_data: Dict[str, Any],
        *,
        course_name: Optional[str] = None,
        source_path: Optional[str] = None,
    ) -> Dict[str, int]:
        if not isinstance(graph_data, dict):
            return {"nodes": 0, "resources": 0}
        course_id = str(course_id or "").strip()
        if not course_id:
            return {"nodes": 0, "resources": 0}

        now = self._now()
        course_name = str(course_name or graph_data.get("name") or course_id)
        source_path = str(source_path or "")
        nodes: List[Dict[str, Any]] = []
        resources: List[Dict[str, Any]] = []

        def walk(node: Dict[str, Any], path: List[str], parent_node_id: Optional[str]) -> None:
            node_name = str(node.get("name") or "").strip()
            if not node_name:
                return
            node_id = str(node.get("node_id") or node.get("id") or node_name).strip()
            node_path = path + [node_name]
            nodes.append(
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_path": node_path,
                    "depth": max(len(node_path) - 1, 0),
                    "parent_node_id": parent_node_id,
                    "payload": node,
                }
            )

            raw_res = node.get("resource_path", [])
            if isinstance(raw_res, str):
                raw_res = [raw_res] if raw_res else []
            if isinstance(raw_res, list):
                for item in raw_res:
                    resource_path = str(item or "").strip()
                    if not resource_path:
                        continue
                    suffix = Path(resource_path).suffix.lower().lstrip(".")
                    resources.append(
                        {
                            "node_id": node_id,
                            "resource_path": resource_path,
                            "resource_type": suffix or None,
                            "title": Path(resource_path).name,
                            "payload": {"resource_path": resource_path, "node_id": node_id},
                        }
                    )

            for child in self._iter_graph_children(node):
                walk(child, node_path, node_id)

        for root_child in self._iter_graph_children(graph_data):
            walk(root_child, [], None)

        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO courses
                (course_id, course_name, source_path, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (course_id, course_name, source_path, self._json(graph_data), now),
            )
            conn.execute("DELETE FROM course_nodes WHERE course_id = ?", (course_id,))
            conn.execute("DELETE FROM resources WHERE course_id = ?", (course_id,))

            for node in nodes:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO course_nodes
                    (course_id, node_id, node_name, node_path_json, depth, parent_node_id, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        node["node_id"],
                        node["node_name"],
                        self._json(node["node_path"]),
                        node["depth"],
                        node["parent_node_id"],
                        self._json(node["payload"]),
                        now,
                    ),
                )

            for resource in resources:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO resources
                    (course_id, node_id, resource_path, resource_type, title, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        resource["node_id"],
                        resource["resource_path"],
                        resource["resource_type"],
                        resource["title"],
                        self._json(resource["payload"]),
                        now,
                        now,
                    ),
                )
        return {"nodes": len(nodes), "resources": len(resources)}

    def record_quiz_attempt(
        self,
        *,
        username: Optional[str],
        user_id: Optional[int],
        course_id: Optional[str],
        node_id: Optional[str],
        score: float,
        total: float,
        passed: bool,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        payload = {
            "username": username,
            "user_id": user_id,
            "course_id": course_id,
            "node_id": node_id,
            "score": score,
            "total": total,
            "passed": bool(passed),
            "extra": extra_payload or {},
        }
        now = self._now()
        with self._lock, self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO quiz_attempts
                (user_id, username, course_id, node_id, score, total, passed, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    course_id,
                    node_id,
                    float(score or 0),
                    float(total or 0),
                    1 if passed else 0,
                    self._json(payload),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def get_course_payload(self, course_id: str) -> Optional[Dict[str, Any]]:
        course_id = str(course_id or "").strip()
        if not course_id:
            return None
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM courses WHERE course_id = ? LIMIT 1",
                (course_id,),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload_json"])
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def get_course_id_by_resource_path(self, resource_path: str) -> Optional[str]:
        resource_path = str(resource_path or "").strip()
        if not resource_path:
            return None
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT course_id
                FROM resources
                WHERE resource_path = ?
                ORDER BY resource_id DESC
                LIMIT 1
                """,
                (resource_path,),
            ).fetchone()
        return str(row["course_id"]) if row and row["course_id"] else None

    def list_learning_nodes_for_course(self, course_id: str) -> List[str]:
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT node_name
                FROM course_nodes
                WHERE course_id = ? AND node_name IS NOT NULL AND trim(node_name) <> ''
                ORDER BY node_name
                """,
                (course_id,),
            ).fetchall()
        return [str(row["node_name"]) for row in rows]

    def list_resources_for_node_name(self, course_id: str, node_name: str) -> List[str]:
        course_id = str(course_id or "").strip()
        node_name = str(node_name or "").strip()
        if not course_id or not node_name:
            return []
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT r.resource_path
                FROM resources r
                JOIN course_nodes n
                  ON n.course_id = r.course_id
                 AND n.node_id = r.node_id
                WHERE r.course_id = ? AND n.node_name = ?
                ORDER BY r.resource_id
                """,
                (course_id, node_name),
            ).fetchall()
        return [str(row["resource_path"]) for row in rows if row["resource_path"]]


_sqlite_store: Optional[SQLiteStore] = None


def get_sqlite_store() -> SQLiteStore:
    global _sqlite_store
    if _sqlite_store is None:
        _sqlite_store = SQLiteStore()
    return _sqlite_store
